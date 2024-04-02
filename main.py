import logging
import asyncio
from fastapi import FastAPI, HTTPException
from tinder import TinderClient
from tinder_token.phone import TinderTokenPhoneV2
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import UploadFile, File
import pandas as pd
from db_handler import DatabaseHandler

# Initialize FastAPI app
app = FastAPI(title='Tinder API',description='This API Provides access to tinder services',debug=True)

# Configure logging
logging.basicConfig(filename='app.log', level=logging.INFO)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Usage example
db_handler = DatabaseHandler('tinder_tokens.db')
db_handler.create_table()  # Create the table


@app.post("/upload_tokens")
async def upload_tokens(file: UploadFile = File(...)):
    if file.content_type != 'text/csv':
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a CSV file.")
    
    try:
        # Read CSV file content into a DataFrame
        df = pd.read_csv(file.file)
        
        # Verify that 'auth_token' column exists
        if 'auth_token' not in df.columns:
            raise HTTPException(status_code=400, detail="CSV file must contain 'auth_token' column.")
        
        # Insert tokens into the database
        db_handler.insert_tokens(df['auth_token'].tolist())
        
        return {"message": "Auth tokens uploaded successfully."}
    except Exception as e:
        logging.error(f"Failed to upload auth tokens: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload auth tokens")
    
@app.post("/upload_token")
async def upload_token(auth_token):
    try:
        # Insert tokens into the database
        db_handler.insert_tokens([auth_token])
        
        return {"message": "Auth token uploaded successfully."}
    except Exception as e:
        logging.error(f"Failed to upload auth tokens: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload auth tokens")


async def send_otp_func(phone_number: str):
    # Attempt to send an OTP code to the phone number
    try:
        phone = TinderTokenPhoneV2()
        sent_otp = await asyncio.to_thread(phone.send_otp_code, phone_number)
        logging.info(f"OTP sent successfully to {phone_number}")
        return sent_otp
    except Exception as e:
        logging.error(f"Failed to send OTP to {phone_number}: {e}")
        return False
    
@app.post("/send_otp")
async def send_otp(phone_number: str):
    sent_otp = await send_otp_func(phone_number)
    if sent_otp:
        return {"message": "OTP sent successfully"}
    else:
        logging.error("Failed to send OTP")
        raise HTTPException(status_code=500, detail="Failed to send OTP")

@app.post("/auth")
async def authenticate_client(phone_number: str,otp_code: str):
    try:
        phone = TinderTokenPhoneV2()
        refresh_token = phone.get_refresh_token(otp_code, phone_number)
        auth_token = phone.get_tinder_token(refresh_token)
        return {"message": "Authentication successful and client stored",'auth_token':auth_token}
    except Exception as e:
        logging.error(f"Authentication failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/update_bio")
async def update_bio(new_bio: str,auth_token:str):
    # Initialize the TinderClient instance and store it globally
    client_instance = TinderClient(auth_token)
    if client_instance is None:
        logging.error("Client not authenticated")
        raise HTTPException(status_code=400, detail="Client not authenticated")
    client_instance.update_bio(new_bio)
    return {"message": "Bio updated successfully"}


@app.get("/get_user_bio")
async def get_user_bio(auth_token: str):
    # Initialize the TinderClient instance with the provided auth_token
    client_instance = TinderClient(auth_token)
    print('client instance created',client_instance)
    if client_instance is None:
        logging.error("Client not authenticated")
        raise HTTPException(status_code=400, detail="Client not authenticated")

    try:
        # Call the get_user_bio method to fetch the user's bio
        user = client_instance.get_self_user()

        # Return the user's bio in the response
        return {"bio": user}
    except Exception as e:
        logging.error(f"Failed to fetch user bio: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user bio")


@app.post("/swipe_routine")
async def swipe_routine(start_hour: int, end_hour: int, likes_per_day: int,auth_token):
    # Initialize the TinderClient instance and store it globally
    client_instance = TinderClient(auth_token)
    if client_instance is None:
        logging.error("Client not authenticated")
        raise HTTPException(status_code=400, detail="Client not authenticated")
    client_instance.swipe_routine(start_hour, end_hour, likes_per_day)
    return {"message": "Swipe routine completed"}



@app.get("/get_auth_tokens")
async def get_auth_tokens():
    
    return {"tokens": db_handler.fetch_all_tokens()}


@app.get("/remove_auth_token")
async def remove_auth_token(auth_token):
    db_handler.remove_token(auth_token)
    return {"tokens": db_handler.fetch_all_tokens()}


# Custom exception handler
@app.exception_handler(Exception)
async def exception_handler(request, exc):
    logging.error(f"An error occurred: {exc}")
    return JSONResponse(status_code=500, content={"message": "Internal Server Error"})



# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/")
async def home():
    return {"Welcome": "Tinder API"}
