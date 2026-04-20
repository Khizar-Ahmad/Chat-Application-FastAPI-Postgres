from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from datetime import datetime, timedelta, timezone
from . import models, schemas
from .auth import hash_password, verify_password, create_access_token, create_refresh_token



async def create_user(db: AsyncSession, user: schemas.UserCreate) -> models.User:
    result        = await db.execute(select(models.User).where(models.User.email == user.email))
    existing      = result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    db_user = models.User(
        name     = user.name,
        email    = user.email,
        password = hash_password(user.password)
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def login(db: AsyncSession, credentials: schemas.UserLogin) -> dict:
    result = await db.execute(select(models.User).where(models.User.email == credentials.email))
    user   = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(credentials.password, user.password):
        raise HTTPException(status_code=400, detail="Invalid email or password")

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