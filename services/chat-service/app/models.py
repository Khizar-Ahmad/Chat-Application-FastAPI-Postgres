import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from .database import Base


class FileType(enum.Enum):
    IMAGE = "image"
    VIDEO = "video"


class Message(Base):
    __tablename__ = "messages"

    id          = Column(Integer, primary_key=True, index=True)
    caption     = Column(String, nullable=True)
    file        = Column(String, nullable=True)
    file_type   = Column(Enum(FileType), nullable=True)
    sender      = Column(Integer, nullable=False)       # plain id, no FK
    receiver    = Column(Integer, nullable=False)       # plain id, no FK
    seen_flag   = Column(Boolean, default=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())