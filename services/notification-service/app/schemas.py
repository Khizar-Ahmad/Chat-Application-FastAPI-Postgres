from pydantic import BaseModel
from typing import Optional


class RegisterDevice(BaseModel):
    userId:      int
    device_type: str    # web, android, ios
    device_id:   str    # FCM token


class DeviceResponse(BaseModel):
    id:          int
    user_id:     int
    token:       str
    device_type: str

    class Config:
        from_attributes = True