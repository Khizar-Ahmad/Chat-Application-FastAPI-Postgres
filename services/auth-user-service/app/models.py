from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from .database import Base


class User(Base):
    __tablename__ = "users"

    id                  = Column(Integer, primary_key=True, index=True)
    name                = Column(String, nullable=False)
    email               = Column(String, unique=True, index=True, nullable=False)
    password            = Column(String, nullable=False)
    avatar              = Column(String, nullable=True)
    is_verified         = Column(Boolean, default=False)
    connection_status   = Column(String, default="offline")
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), onupdate=func.now())


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, nullable=False)
    token       = Column(String, unique=True, nullable=False)
    is_revoked  = Column(Boolean, default=False)
    expires_at  = Column(DateTime(timezone=True), nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

class OTPVerification(Base):                                # NEW
    __tablename__ = "otp_verifications"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, nullable=False)
    email       = Column(String, nullable=False)
    otp         = Column(String, nullable=False)            # 6 digit code
    is_used     = Column(Boolean, default=False)
    expires_at  = Column(DateTime(timezone=True), nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, nullable=False)
    email       = Column(String, nullable=False)
    token       = Column(String, unique=True, nullable=False)
    is_used     = Column(Boolean, default=False)
    expires_at  = Column(DateTime(timezone=True), nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())