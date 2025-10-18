from pydantic import BaseModel
from typing import Optional

class UserBase(BaseModel):
    name: str
    email: str
    password: str
class UserCreate(UserBase):
    pass

class UserResponse(BaseModel):
    # id: int
    name:str
    email:str
    connection_status:str
    class Config:
        orm_mode = True


# class UserMessages(BaseModel):
#     # id: int
#     caption:str
#     sender:str
#     receiver:str
#     seen_flag:bool


    class Config:
        orm_mode = True
        
class login(BaseModel):
    email: str
    password: str

class SendMessages(BaseModel):
    id: int
    caption: Optional[str] = None
    file: Optional[str] = None
    file_type: Optional[str] = None
    sender: int
    receiver: int
    seen_flag: bool = False  # default False
