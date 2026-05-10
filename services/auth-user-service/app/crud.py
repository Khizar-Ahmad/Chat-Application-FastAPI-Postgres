from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from datetime import datetime, timedelta, timezone
from . import models, schemas
from .auth import hash_password, verify_password, create_access_token, create_refresh_token
from .sendgrid_email import send_otp_email,send_password_reset_email
import random
import secrets


async def create_user(db: AsyncSession, user: schemas.UserCreate) -> models.User:
    result        = await db.execute(select(models.User).where(models.User.email == user.email))
    existing      = result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=409, detail={"status":"warning","message":"Email already registered"})

    db_user = models.User(
        name     = user.name,
        email    = user.email,
        password = hash_password(user.password)
    )
    try:
        db.add(db_user)

        await db.flush()

        await create_and_send_otp(db,db_user.id,db_user.email,db_user.name)

        await db.commit()
        return {
            "id":    db_user.id,
            "name":  db_user.name,
            "email": db_user.email,
            "connection_status": db_user.connection_status,
            "detail": "Signed-Up successfully, Now verify your account",
            "avatar": db_user.avatar
        }
    except Exception:
        await db.rollback()
        raise
    # await db.refresh(db_user)
    # return db_user


async def login(db: AsyncSession, credentials: schemas.UserLogin) -> dict:
    result = await db.execute(select(models.User).where(models.User.email == credentials.email))
    user   = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail={"status":"error","message":"User not found"})

    if not verify_password(credentials.password, user.password):
        raise HTTPException(status_code=400, detail={"status":"error","message":"Invalid email or password"})
    
    if not user.is_verified:
        await create_and_send_otp(db,user.id,user.email,user.name)
        await db.commit()
        raise HTTPException(status_code=403, detail={"status":"warning","message":"Account not verified yet. OTP sent via email, please check it"})

    access_token  = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    # store refresh token
    db_token = models.RefreshToken(
        user_id    = user.id,
        token      = refresh_token,
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    )
    db.add(db_token)
    await db.commit()

    return {
        "user": {
            "id":    user.id,
            "name":  user.name,
            "email": user.email,
            "connection_status": user.connection_status,
            "avatar": user.avatar
        },
        "token": access_token
    }


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> dict:
    result   = await db.execute(
        select(models.RefreshToken).where(
            models.RefreshToken.token      == refresh_token,
            models.RefreshToken.is_revoked == False
        )
    )
    db_token = result.scalar_one_or_none()

    if not db_token:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if db_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    new_token = create_access_token({"sub": str(db_token.user_id)})
    return {"token": new_token}



async def logout(db: AsyncSession, refresh_token: str) -> dict:
    result   = await db.execute(
        select(models.RefreshToken).where(models.RefreshToken.token == refresh_token)
    )
    db_token = result.scalar_one_or_none()

    if db_token:
        db_token.is_revoked = True
        await db.commit()

    return {"status": "success", "message": "Logged out successfully"}




async def get_user_by_id(db: AsyncSession, user_id: int) -> models.User:
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user   = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user




async def get_user_by_email(db: AsyncSession, email: str) -> models.User:
    result = await db.execute(select(models.User).where(models.User.email == email))
    user   = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user




async def get_all_users_except(db: AsyncSession, exclude_id: int) -> list[models.User]:
    result = await db.execute(select(models.User).where(models.User.id != exclude_id))
    return result.scalars().all()


async def update_connection_status(db: AsyncSession, user_id: int, connection_status: str) -> dict:
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user   = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.connection_status = connection_status
    await db.commit()
    await db.refresh(user)
    return {"status": "success", "connection_status": user.connection_status}

def generate_otp() -> str:
    return str(random.randint(100000, 999999))

async def create_and_send_otp(
    db: AsyncSession,
    user_id: int,
    email: str,
    name: str
) -> None:
    otp         = generate_otp()
    expires_at  = datetime.now(timezone.utc) + timedelta(minutes=1,
        seconds=13)

    # invalidate any existing unused OTPs for this user
    existing_otps = await db.execute(
        select(models.OTPVerification).where(
            models.OTPVerification.user_id  == user_id,
            models.OTPVerification.is_used  == False
        )
    )
    for existing_otp in existing_otps.scalars().all():
        existing_otp.is_used = True

    # create new OTP
    db_otp = models.OTPVerification(
        user_id     = user_id,
        email       = email,
        otp         = otp,
        expires_at  = expires_at
    )
    db.add(db_otp)
    await db.flush()

    # send email
    await send_otp_email(email, otp, name)


# ── Verify OTP ────────────────────────────────────────────────

async def verify_otp(db: AsyncSession, payload: schemas.OTPVerifyRequest) -> dict:
    # find user
    result  = await db.execute(select(models.User).where(models.User.email == payload.email))
    user    = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail={"status":"error","message": "User not found, with this email."})
        

    if user.is_verified:
        raise HTTPException(status_code=400, detail={"status":"warning","message": "Account already verified."})
    


    # find valid OTP
    otp_result  = await db.execute(
        select(models.OTPVerification).where(
            models.OTPVerification.user_id  == user.id,
            models.OTPVerification.otp      == payload.otp,
            models.OTPVerification.is_used  == False
        )
    )
    db_otp = otp_result.scalar_one_or_none()

    if not db_otp:
        raise HTTPException(status_code=400, detail={"status":"error","message":"Invalid OTP"})

    if db_otp.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail={"status":"error","message":"OTP has expired"})


    # mark OTP as used
    db_otp.is_used      = True

    # mark user as verified
    user.is_verified    = True

    await db.commit()
    
    await db.refresh(user)
    access_token  = create_access_token({"sub": str(user.id)})


    return {
        "user": {
            "id":    user.id,
            "name":  user.name,
            "email": user.email,
            "connection_status": user.connection_status,
            "detail": "Account Verified Successfully... Logged In",
            "avatar": user.avatar
        },
        "token": access_token
    }



# ── Resend OTP ────────────────────────────────────────────────

async def resend_otp(db: AsyncSession, payload: schemas.ResendOTPRequest) -> dict:
    result  = await db.execute(select(models.User).where(models.User.email == payload.email))
    user    = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail={"status":"error","message":"User not found"})

    if user.is_verified:
        raise HTTPException(status_code=400, detail={"status":"warning","message":"Account already verified"})

    await create_and_send_otp(db, user.id, user.email, user.name)
    await db.commit()
    res = {"detail":{"status":"success","message": "New OTP sent to your email"}}
    return res

async def forgot_password(
    db: AsyncSession,
    payload: schemas.ForgotPasswordRequest
) -> dict:
    result  = await db.execute(
        select(models.User).where(models.User.email == payload.email)
    )
    user    = result.scalar_one_or_none()

    # always return success even if email not found
    # this prevents email enumeration attacks
    if not user:
        return {"detail":{"status":"info","message":"If this email exists you will receive a reset link shortly."}}

    # invalidate any existing unused reset tokens
    existing = await db.execute(
        select(models.PasswordResetToken).where(
            models.PasswordResetToken.user_id == user.id,
            models.PasswordResetToken.is_used == False
        )
    )
    for token in existing.scalars().all():
        token.is_used = True

    # generate secure token
    reset_token = secrets.token_urlsafe(32)
    expires_at  = datetime.now(timezone.utc) + timedelta(minutes=10)

    db_token = models.PasswordResetToken(
        user_id    = user.id,
        email      = user.email,
        token      = reset_token,
        expires_at = expires_at
    )
    db.add(db_token)
    await db.commit()

    # send email
    await send_password_reset_email(user.email, user.name, reset_token)

    return {"detail":{"status":"info","message":"If this email exists you will receive a reset link shortly."}}


# ── Reset Password (from email link) ─────────────────────────

async def reset_password(
    db: AsyncSession,
    payload: schemas.ResetPasswordRequest
) -> dict:
    # find token
    result      = await db.execute(
        select(models.PasswordResetToken).where(
            models.PasswordResetToken.token   == payload.token,
            models.PasswordResetToken.is_used == False
        )
    )
    db_token    = result.scalar_one_or_none()

    if not db_token:
        raise HTTPException(status_code=400, detail={"status":"error","message":"Invalid or already used reset link"})

    if db_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail={"status":"error","message":"Reset link has expired"})

    # get user
    user_result = await db.execute(
        select(models.User).where(models.User.id == db_token.user_id)
    )
    user        = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail={"status":"error","message":"User not found"})

    # update password
    user.password       = hash_password(payload.new_password)
    db_token.is_used    = True

    # revoke all refresh tokens for security
    await db.execute(
        select(models.RefreshToken).where(
            models.RefreshToken.user_id == user.id
        )
    )

    await db.commit()

    return {"detail":{"status":"success","message":"Password reset successfully. You can now login with your new password."}}

