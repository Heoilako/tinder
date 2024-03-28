from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from tinder import TinderClient
from tinder_token.phone import TinderTokenPhoneV2
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=False,
#     allow_methods=["GET", "POST", "PUT", "DELETE"],
#     allow_headers=["*"],
# )
# Placeholder for storing the phone number after the OTP is sent
global_phone_number = None

# Placeholder for the global TinderClient instance
global_client_instance = None

class AuthToken:
    def __init__(self) -> None:
        self.phone = TinderTokenPhoneV2()

    def send_otp(self, phone_number: str):
        # Attempt to send an OTP code to the phone number
        try:
            return self.phone.send_otp_code(phone_number)
        except Exception as e:
            print(e)  # Ideally, log the error
            return False
    
    def get_auth_token(self, otp_code: str) -> str:
        if global_phone_number is None:
            raise ValueError("Phone number is not set.")
        refresh_token = self.phone.get_refresh_token(otp_code, global_phone_number)
        return self.phone.get_tinder_token(refresh_token)



@app.post("/send_otp/")
async def send_otp(phone_number: str):
    global global_phone_number
    auth = AuthToken()
    sent_otp=auth.send_otp(phone_number)
    if sent_otp:
        # Store the phone number globally after successfully sending OTP
        global_phone_number = phone_number
        return {"message": "OTP sent successfully "+str(sent_otp)}
    else:
        raise HTTPException(status_code=500, detail="Failed to send OTP")

@app.post("/auth/")
async def authenticate_and_store_client(otp_code):
    global global_client_instance
    if global_phone_number is None:
        raise HTTPException(status_code=400, detail="Phone number not found. Please send OTP first.")
    
    auth = AuthToken()
    try:
        auth_token = auth.get_auth_token(otp_code)
        # Initialize the TinderClient instance and store it globally
        global_client_instance = TinderClient(auth_token)
        return {"message": "Authentication successful and client stored"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/update_bio/")
async def update_bio(new_bio: str):
    if global_client_instance is None:
        raise HTTPException(status_code=400, detail="Client not authenticated")
    global_client_instance.update_bio(new_bio)
    return {"message": "Bio updated successfully"}

@app.post("/swipe_routine/")
async def swipe_routine(min_age: int, max_age: int, count: int):
    if global_client_instance is None:
        raise HTTPException(status_code=400, detail="Client not authenticated")
    global_client_instance.swipe_routine(min_age, max_age, count)
    return {"message": "Swipe routine completed"}

#if __name__ == "__main__":
    # uvicorn.run(app, host="0.0.0.0", port=8000)
