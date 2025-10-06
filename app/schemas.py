from pydantic import BaseModel
from typing import Optional

class UserBase(BaseModel):
    name: str
    email: str
    password: str
class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: int

    class Config:
        orm_mode = True
        
class login(BaseModel):
    email: str
    password: str

class SendMessage(BaseModel):
    caption: Optional[str] = None
    file: Optional[str] = None
    file_type: Optional[str] = None
    sender: int
    receiver: int
    seen_flag: bool = False  # default False
