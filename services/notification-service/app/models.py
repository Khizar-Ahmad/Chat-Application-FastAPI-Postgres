from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from .database import Base


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, nullable=False, index=True)   # plain id, no FK
    token       = Column(String, nullable=False)                 # FCM token
    device_type = Column(String, nullable=False)                 # web, android, ios
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, nullable=False)
    message_id  = Column(Integer, nullable=True)
    title       = Column(String, nullable=False)
    body        = Column(String, nullable=False)
    is_sent     = Column(Boolean, default=False)
    error       = Column(String, nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())