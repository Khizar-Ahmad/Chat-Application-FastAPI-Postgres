from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, update,case, func, desc
from fastapi import HTTPException
from . import models, schemas
from .http_client import get_all_users_except, get_user_by_id
from .websocket_manager import manager
from .http_client import update_user_status





async def get_users(db: AsyncSession, current_user_id: int) -> dict:
  
    users = await get_all_users_except(current_user_id)

    
    result = {
        user["id"]: {
            "userInfo": user,
            "data": [],
            "message":"",
            "file_type":None
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

    conversation_partner = case(
        (
            models.Message.sender == current_user_id,
            models.Message.receiver
        ),
        else_=models.Message.sender
    ).label("conversation_partner")

    subquery = (
        select(
            conversation_partner,
            func.max(models.Message.created_at).label("latest_time")
        )
        .where(
            or_(
                models.Message.sender == current_user_id,
                models.Message.receiver == current_user_id
            )
        )
        .group_by(conversation_partner)
        .subquery()
    )

    lastMessages = await db.execute(
        select(models.Message)
        .join(
            subquery,
            (
                (
                    case(
                        (
                            models.Message.sender == current_user_id,
                            models.Message.receiver
                        ),
                        else_=models.Message.sender
                    )
                    == subquery.c.conversation_partner
                )
                &
                (
                    models.Message.created_at
                    == subquery.c.latest_time
                )
            )
        )
        .order_by(desc(models.Message.created_at))
    )

    latest_messages = lastMessages.scalars().all()
    

    for msg in unseen_messages:
        if msg.sender in result:
            result[msg.sender]["data"].append(msg)


    for msg in latest_messages:
        if msg.sender in result:
            result[msg.sender]["message"]=msg.caption
            result[msg.sender]["file_type"]=msg.file_type
        elif msg.receiver in result:
            result[msg.receiver]["message"]=msg.caption
            result[msg.receiver]["file_type"]=msg.file_type

    print("this is the response",result)
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



async def update_messages_status(db: AsyncSession, payload) -> dict:
    await db.execute(
        update(models.Message)
        .where(models.Message.id.in_(payload.message_ids))
        .values(seen_flag=True)
    )
    await db.commit()
    if payload.sender in manager.active_connections:
        seen_payload = {
            "messages_seen": True,
            "message_ids":  payload.message_ids,
            "sender":       payload.sender,
            "receiver":     payload.receiver,
        }
        try:
            await manager.active_connections[payload.sender].send_json(seen_payload)
        except Exception as e:
            print(f"Failed to send to sender back: {payload.sender}: {e}")
            # remove dead connection
            if payload.sender in manager.active_connections:
                del manager.active_connections[payload.sender]
                await update_user_status(payload.sender, "offline")
                print(f"Removed dead connection for user {payload.sender}")

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