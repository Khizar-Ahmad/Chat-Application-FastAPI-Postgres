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
        # self.active_connections: dict[int, WebSocket] = {}
        self.active_connections: dict[int, set[WebSocket]] = {}

    

    def _is_user_online(self, user_id: int) -> bool:
        return (
            user_id in self.active_connections and
            len(self.active_connections[user_id]) > 0
        )
    async def connect(self, websocket: WebSocket, email: str):
        await websocket.accept()

        user = await get_user_by_email(email)

        if user is None:
            await websocket.close()
            return

        user_id = user["id"]
        # self.active_connections[user_id] = 
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()

        self.active_connections[user_id].add(websocket)
        print(f"User {email} connected. Total connections for this user: "
              f"{len(self.active_connections[user_id])}")
        
        if len(self.active_connections[user_id]) == 1:
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
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].discard(websocket)

                if len(self.active_connections[user_id])==0:
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
            for ws in list(self.active_connections[message.sender]):
                try:
                    await ws.send_json(payload)
                except Exception as e:
                    print(f"Failed to send to sender back: {message.sender}: {e}")
                    # remove dead connection
                    if message.sender in self.active_connections and len(self.active_connections[message.sender])>0:
                        self.active_connections[message.sender].discard(ws)
                        print(f"Total live connections for user: {message.sender} is {len(self.active_connections[message.sender])}")
                        if len(self.active_connections[message.sender])==0:
                            await update_user_status(message.sender, "offline")
                            del self.active_connections[message.sender]
                            print(f"Removed dead connection for user {message.sender}")
        if message.receiver in self.active_connections:
            for ws in list(self.active_connections[message.receiver]):
                try: 
                    await ws.send_json(payload)
                except Exception as e:
                    print(f"Failed to send to receiver back: {message.receiver}: {e}")
                    # remove dead connection
                    if message.receiver in self.active_connections and len(self.active_connections[message.receiver])>0:
                        self.active_connections[message.receiver].discard(ws)
                        print(f"Total live connections for user: {message.receiver} is {len(self.active_connections[message.receiver])}")
                        if len(self.active_connections[message.receiver])==0:
                            await update_user_status(message.receiver, "offline")
                            del self.active_connections[message.receiver]
                            print(f"Removed dead connection for user {message.receiver}")
                    # if message.receiver in self.active_connections:
                    #     del self.active_connections[message.receiver]
                    #     await update_user_status(message.receiver, "offline")
                    #     print(f"Removed dead connection for user {message.receiver}")  
        await publish_message_sent_event({
            "message_id":    message.id,
            "sender_id":     message.sender,
            "receiver_id":   message.receiver,
            "caption":       message.caption,
            "receiver_online": message.receiver in self.active_connections
        })


    async def change_message_status(self, parsed: dict):
        async with SessionLocal() as db:
    
            await db.execute(
            sql_update(models.Message)
            .where(models.Message.id == parsed["id"])
            .values(seen_flag=True)
            )

            await db.commit()

            payload = {
            "id":           parsed["id"],
            "seen_flag":    True,
            "caption":      parsed["caption"],
            "sender": parsed["sender"],
            "receiver": parsed["receiver"],
            "created_at":   parsed["created_at"]
             }

            sender_id = parsed.get("sender")

            if sender_id in self.active_connections:
                for ws in list(self.active_connections[sender_id]):
                    try:
                        await ws.send_json(payload)
                    except Exception as e:
                        print(f"Failed to send to sender back: {sender_id}: {e}")
                        # remove dead connection
                        if sender_id in self.active_connections and len(self.active_connections[sender_id])>0:
                            self.active_connections[sender_id].discard(ws)
                            print(f"Total live connections for user: {sender_id} is {len(self.active_connections[sender_id])}")
                            if len(self.active_connections[sender_id])==0:
                                await update_user_status(sender_id, "offline")
                                del self.active_connections[sender_id]
                                print(f"Removed dead connection for user {sender_id}")

            # try:
            #     await self.active_connections[sender_id].send_json(payload)
            # except Exception as e:
            #     print(f"Failed to send to sender back: {sender_id}: {e}")
            #     # remove dead connection
            #     if sender_id in self.active_connections:
            #         del self.active_connections[sender_id]
            #         await update_user_status(sender_id, "offline")
            #         print(f"Removed dead connection for user {sender_id}")



    async def broadcast_connection_news(self, message: dict):
        # for user_id, ws in self.active_connections.items():
        #     if user_id == message["userId"]:
        #         continue
        #     await ws.send_json(message)

        exclude_user=message["userId"]
        dead_connections = []

        for user_id, connections in list(self.active_connections.items()):
            if user_id == exclude_user:
                continue

            for ws in list(connections):
                try:
                    await ws.send_json(message)
                except Exception as e:
                    print(f"Dead connection for user {user_id}: {e}")
                    dead_connections.append((user_id, ws))

        # clean up dead connections
        for user_id, ws in dead_connections:
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(ws)
                if len(self.active_connections[user_id]) == 0:
                    del self.active_connections[user_id]
                    await update_user_status(user_id, "offline")



        # dead_connections = []

        # for user_id, ws in self.active_connections.items():
        #     if user_id == message["userId"]:
        #         continue
        #     try:
        #         await ws.send_json(message)
        #     except Exception as e:
                
        #         print(f"Dead connection detected for user {user_id}: {e}")
        #         dead_connections.append(user_id)

        
        # for user_id in dead_connections:
        #     if user_id in self.active_connections:
        #         del self.active_connections[user_id]
        #         await update_user_status(user_id, "offline")
        #         print(f"Cleaned up dead connection for user {user_id}")



manager = ConnectionManager()