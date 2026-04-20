from fastapi import WebSocket
from .database import SessionLocal
from .http_client import get_user_by_email, update_user_status
from sqlalchemy import select, update as sql_update
from . import models
import json
from .rabbitmq import publish_message_sent_event


class ConnectionManager:
    def __init__(self):
        # same structure as your original — { user_id: WebSocket }
        self.active_connections: dict[int, WebSocket] = {}

    async def connect(self, websocket: WebSocket, email: str):
        await websocket.accept()

        user = await get_user_by_email(email)

        if user is None:
            await websocket.close()
            return

        user_id = user["id"]
        self.active_connections[user_id] = websocket

        await update_user_status(user_id, "online")

        print(f"User {email} connected with id {user_id}")

        payload = {
            "userId":           user_id,
            "connectionNews":   "user_connected",
            "connection_status": "online"
        }
        await self.broadcast_connection_news(payload)


    async def disconnect(self, websocket: WebSocket):
        print(self.active_connections)
        for user_id, ws in list(self.active_connections.items()):
            if ws == websocket:
                del self.active_connections[user_id]

                await update_user_status(user_id, "offline")

                print(f"User {user_id} disconnected")

                payload = {
                    "userId":           user_id,
                    "connectionNews":   "user_disconnected",
                    "connection_status": "offline"
                }
                await self.broadcast_connection_news(payload)
                break


    async def send_personal_message(self, parsed: dict):

        async with SessionLocal() as db:
            message = models.Message(
                caption     = parsed["message"],
                sender      = int(parsed["sender"]),
                receiver    = int(parsed["receiver"])
            )
            db.add(message)
            await db.commit()
            await db.refresh(message)

        payload = {
            "id":           message.id,
            "caption":      message.caption,
            "sender":       message.sender,
            "receiver":     message.receiver,
            "seen_flag":    message.seen_flag,
            "created_at":   str(message.created_at)
        }

        if message.sender in self.active_connections:
            await self.active_connections[message.sender].send_json(payload)

        if message.receiver in self.active_connections:
            await self.active_connections[message.receiver].send_json(payload)

        await publish_message_sent_event({
            "message_id":    message.id,
            "sender_id":     message.sender,
            "receiver_id":   message.receiver,
            "caption":       message.caption,
            "receiver_online": message.receiver in self.active_connections
        })


    async def change_message_status(self, parsed: dict):
        message= parsed
        async with SessionLocal() as db:
            await db.execute(
                sql_update(models.Message)
                .where(models.Message.id == message.id)
            )
            message.seen_flag=True
            await db.add(message)
            await db.commit()
            await db.refresh(message)



    async def broadcast_connection_news(self, message: dict):
        for user_id, ws in self.active_connections.items():
            if user_id == message["userId"]:
                continue
            await ws.send_json(message)


manager = ConnectionManager()