import logging
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from tinder import TinderClient
from tinder_token.phone import TinderTokenPhoneV2
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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

@app.post("/swipe_routine")
async def swipe_routine(start_hour: int, end_hour: int, likes_per_day: int,auth_token):
    # Initialize the TinderClient instance and store it globally
    client_instance = TinderClient(auth_token)
    if client_instance is None:
        logging.error("Client not authenticated")
        raise HTTPException(status_code=400, detail="Client not authenticated")
    client_instance.swipe_routine(start_hour, end_hour, likes_per_day)
    return {"message": "Swipe routine completed"}

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
