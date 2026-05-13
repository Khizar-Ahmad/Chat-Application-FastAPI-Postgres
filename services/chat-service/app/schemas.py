from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class FileType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"


class MessageResponse(BaseModel):
    id:         int
    caption:    Optional[str]
    file:       Optional[str]
    file_type:  Optional[FileType]
    sender:     int
    receiver:   int
    seen_flag:  bool
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class UserInfo(BaseModel):
    id:                 int
    name:               str
    email:              str
    connection_status:  str



class UserWithUnseenMessages(BaseModel):
    userInfo:   UserInfo
    data:       list[MessageResponse]



class ConversationResponse(BaseModel):
    userInfo:   UserInfo
    data:       list[MessageResponse]

class UpdateSeenStatus(BaseModel):
    sender:int
    receiver:int
    message_ids: list[int]


class WSMessagePayload(BaseModel):
    message:    str
    sender:     int
    receiver:   int


class WSSeenPayload(BaseModel):
    changeStatus:   bool
    message_id:     int