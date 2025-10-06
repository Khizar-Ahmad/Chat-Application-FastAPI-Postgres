from sqlalchemy import Column, Integer,String, ForeignKey,Boolean,Enum
from .database import Base
import enum


class FileType(enum.Enum):
    IMAGE = "image"
    VIDEO = "video"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    connection_status= Column(String, default='offline')
    socket_id= Column(String, nullable=True)

class Message(Base):
    __tablename__='messages'
    id = Column(Integer,primary_key=True,index=True)
    caption= Column(String, nullable=True)
    file= Column(String, nullable=True)
    file_type= Column(Enum(FileType), nullable=True)
    sender= Column(ForeignKey("users.id"))
    receiver= Column(ForeignKey("users.id"))
    seen_flag = Column(Boolean, default=False)




