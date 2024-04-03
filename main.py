import logging
import asyncio
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
from tinder import TinderClient
from tinder_token.phone import TinderTokenPhoneV2
from db_handler import DatabaseHandler  # Make sure this class has the necessary updates for group and proxy management
from io import StringIO

# Initialize FastAPI app
app = FastAPI(title='Tinder API', description='This API Provides access to Tinder services', debug=True)

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

# Global dictionary for storing TinderClient instances keyed by auth token
client_instances = {}

# Initialize DatabaseHandler with proxy and group support
db_handler = DatabaseHandler('tinder_tokens.db')

def get_tinder_client(auth_token: str) -> TinderClient:
    """Fetches or creates a TinderClient instance with proxy settings."""
    if auth_token not in client_instances:
        proxy_info = db_handler.fetch_proxy_for_token(auth_token)
        client_instances[auth_token] = TinderClient(auth_token, proxy_info)
    return client_instances[auth_token]

@app.post("/upload_tokens")
async def upload_tokens(request: Request):
    if request.headers.get('content-type') != 'text/csv':
        raise HTTPException(status_code=400, detail="Invalid Content-Type header. Please use 'text/csv'.")

    try:
        body_bytes = await request.body()
        body_str = body_bytes.decode("utf-8")
        string_io = StringIO(body_str)
        df = pd.read_csv(string_io)

        required_columns = ['auth_token', 'http_proxy', 'https_proxy']
        for column in required_columns:
            if column not in df.columns:
                raise HTTPException(status_code=400, detail=f"CSV file must contain '{column}' column.")

        tokens_with_proxies = list(df[['auth_token', 'http_proxy', 'https_proxy']].to_records(index=False))
        db_handler.insert_tokens(tokens_with_proxies)
        return {"message": "Auth tokens with proxies uploaded successfully."}
    except Exception as e:
        logging.error(f"Failed to upload auth tokens with proxies: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload auth tokens with proxies")

@app.post("/upload_token")
async def upload_token(auth_token: str, http_proxy: str = None, https_proxy: str = None):
    try:
        db_handler.insert_tokens([(auth_token, http_proxy, https_proxy)])
        return {"message": "Auth token uploaded successfully."}
    except Exception as e:
        logging.error(f"Failed to upload auth token: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload auth token")

async def send_otp_func(phone_number: str):
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
async def authenticate_client(phone_number: str, otp_code: str):
    try:
        phone = TinderTokenPhoneV2()
        refresh_token = phone.get_refresh_token(otp_code, phone_number)
        auth_token = phone.get_tinder_token(refresh_token)
        return {"message": "Authentication successful", 'auth_token': auth_token}
    except Exception as e:
        logging.error(f"Authentication failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/update_bio")
async def update_bio(new_bio: str, auth_token: str):
    client_instance = get_tinder_client(auth_token)
    try:
        client_instance.update_bio(new_bio)
        return {"message": "Bio updated successfully"}
    except Exception as e:
        logging.error(f"Failed to update bio: {e}")
        raise HTTPException(status_code=500, detail="Failed to update bio")

@app.get("/get_user_bio")
async def get_user_bio(auth_token: str):
    client_instance = get_tinder_client(auth_token)
    try:
        user_bio = client_instance.get_user_bio()
        return {"bio": user_bio}
    except Exception as e:
        logging.error(f"Failed to fetch user bio: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user bio")

@app.post("/swipe_routine")
async def swipe_routine(start_hour: int, end_hour: int, likes_per_day: int, auth_token: str):
    client_instance = get_tinder_client(auth_token)
    try:
        client_instance.swipe_routine(start_hour, end_hour, likes_per_day)
        return {"message": "Swipe routine completed"}
    except Exception as e:
        logging.error(f"Failed to complete swipe routine: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete swipe routine")

@app.post("/create_group")
async def create_group(group_name: str):
    try:
        db_handler.create_group(group_name)
        return {"message": f"Group '{group_name}' created successfully."}
    except Exception as e:
        logging.error(f"Failed to create group '{group_name}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create group '{group_name}': {e}")

@app.delete("/remove_group")
async def remove_group(group_name: str):
    try:
        db_handler.remove_group(group_name)
        return {"message": f"Group '{group_name}' removed successfully."}
    except Exception as e:
        logging.error(f"Failed to remove group '{group_name}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove group '{group_name}': {e}")
    

@app.delete("/get_groups")
async def get_groups():
    try:
        response=db_handler.get_groups()
        return {"groups": response}
    except Exception as e:
        logging.error(f"Failed to get groups: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get groups: {e}")
    
    
@app.post("/add_token_to_group")
async def add_token_to_group(auth_token:str,group_name: str):
    try:
        db_handler.add_token_to_group(group_name)
        return {"message": f"Group '{group_name}' removed successfully."}
    except Exception as e:
        logging.error(f"Failed to Add Token to group '{group_name}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to Add Token to group '{group_name}': {e}")
    

@app.post("/remove_token_from_group")
async def remove_token_from_group(auth_token:str,group_name: str):
    try:
        db_handler.remove_token_from_group(auth_token,group_name)
        return {"message": f"Group '{group_name}' removed successfully."}
    except Exception as e:
        logging.error(f"Failed to remove Token to group '{group_name}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove Token to group '{group_name}': {e}")

@app.post("/update_group_bio")
async def update_group_bio(group_name: str, new_bio: str):
    try:
        auth_tokens = db_handler.fetch_group_tokens(group_name)
        for token in auth_tokens:
            client_instance = get_tinder_client(token)
            client_instance.update_bio(new_bio)
        return {"message": f"Bios updated for all members of group '{group_name}'."}
    except Exception as e:
        logging.error(f"Failed to update bios for group '{group_name}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update bios for group: {e}")

@app.get("/get_auth_tokens")
async def get_auth_tokens():
    return {"tokens": db_handler.fetch_all_tokens()}

@app.get("/get_group_auth_tokens")
async def get_group_auth_tokens(group_name:str):
    return {"tokens": db_handler.fetch_group_tokens(group_name)}

@app.get("/remove_auth_token")
async def remove_auth_token(auth_token: str):
    client_instances.pop(auth_token, None)  # Remove the client instance if it exists
    db_handler.remove_token(auth_token)  # Remove the token from the database
    return {"message": "Auth token removed successfully"}

@app.exception_handler(Exception)
async def exception_handler(request, exc):
    logging.error(f"An error occurred: {exc}")
    return JSONResponse(status_code=500, content={"message": "Internal Server Error"})

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/")
async def home():
    return {"Welcome": "Tinder API"}
