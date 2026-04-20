from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from . import models, schemas



async def register_device(db: AsyncSession, payload: schemas.RegisterDevice) -> models.DeviceToken:
    # check if device_type already registered for this user
    result = await db.execute(
        select(models.DeviceToken).where(
            models.DeviceToken.user_id     == payload.userId,
            models.DeviceToken.device_type == payload.device_type
        )
    )
    device = result.scalar_one_or_none()

    if device:
        # update existing token
        device.token = payload.device_id
    else:
        # create new
        device = models.DeviceToken(
            user_id     = payload.userId,
            token       = payload.device_id,
            device_type = payload.device_type
        )
        db.add(device)

    await db.commit()
    await db.refresh(device)
    return device



async def get_user_devices(db: AsyncSession, user_id: int) -> list[models.DeviceToken]:
    result = await db.execute(
        select(models.DeviceToken).where(models.DeviceToken.user_id == user_id)
    )
    return result.scalars().all()


# ── Log notification ──────────────────────────────────────────

async def log_notification(
    db: AsyncSession,
    user_id: int,
    message_id: int,
    title: str,
    body: str,
    is_sent: bool,
    error: str = None
) -> None:
    log = models.NotificationLog(
        user_id    = user_id,
        message_id = message_id,
        title      = title,
        body       = body,
        is_sent    = is_sent,
        error      = error
    )
    db.add(log)
    await db.commit()