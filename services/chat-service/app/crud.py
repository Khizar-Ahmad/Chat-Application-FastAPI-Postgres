from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, update
from fastapi import HTTPException
from . import models, schemas
from .http_client import get_all_users_except, get_user_by_id




async def get_users(db: AsyncSession, current_user_id: int) -> dict:
  
    users = await get_all_users_except(current_user_id)

    
    result = {
        user["id"]: {
            "userInfo": user,
            "data": []
        }
        for user in users
    }

    unseen_result = await db.execute(
        select(models.Message).where(
            models.Message.receiver == current_user_id,
            models.Message.seen_flag == False
        )
    )
    unseen_messages = unseen_result.scalars().all()


    for msg in unseen_messages:
        if msg.sender in result:
            result[msg.sender]["data"].append(msg)

    return result



async def get_messages_between_users(
    db: AsyncSession,
    sender_id: int,
    receiver_id: int
) -> dict:
 
    receiver = await get_user_by_id(receiver_id)

    if not receiver:
        return {"error": "Receiver not found", "data": []}

    
    result = await db.execute(
        select(models.Message).where(
            or_(
                and_(
                    models.Message.sender == sender_id,
                    models.Message.receiver == receiver_id
                ),
                and_(
                    models.Message.sender == receiver_id,
                    models.Message.receiver == sender_id
                )
            )
        ).order_by(models.Message.created_at)
    )
    messages = result.scalars().all()

  
    return {
        "userInfo": {
            "id":               receiver["id"],
            "name":             receiver["name"],
            "email":            receiver["email"],
            "connection_status": receiver["connection_status"],
        },
        "data": messages
    }



async def update_messages_status(db: AsyncSession, message_ids: list[int]) -> dict:
    await db.execute(
        update(models.Message)
        .where(models.Message.id.in_(message_ids))
        .values(seen_flag=True)
    )
    await db.commit()
    return {"status": "success", "message": "messages status updated successfully"}



async def save_message(db: AsyncSession, sender: int, receiver: int, caption: str) -> models.Message:
    message = models.Message(
        caption     = caption,
        sender      = sender,
        receiver    = receiver
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message



async def mark_message_seen(db: AsyncSession, message_id: int) -> None:
    await db.execute(
        update(models.Message)
        .where(models.Message.id == message_id)
        .values(seen_flag=True)
    )
    await db.commit()