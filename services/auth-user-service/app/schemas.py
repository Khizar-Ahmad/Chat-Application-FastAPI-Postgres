from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    name:     str
    email:    EmailStr
    password: str


class UserLogin(BaseModel):
    email:    EmailStr
    password: str


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class UpdateConnectionStatus(BaseModel):
    user_id:            int
    connection_status:  str


class UserResponse(BaseModel):
    id:                 int
    name:               str
    email:              str
    avatar:             Optional[str] = None
    connection_status:  str
    created_at:         Optional[datetime] = None

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    user:   UserResponse
    token:  str


class RefreshResponse(BaseModel):
    token: str



class InternalUserResponse(BaseModel):
    id:                 int
    name:               str
    email:              str
    avatar:             Optional[str] = None
    connection_status:  str

    class Config:
        from_attributes = True