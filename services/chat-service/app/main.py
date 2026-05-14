from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect,File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from . import crud, schemas, models
from .database import get_db, engine,SessionLocal
from .dependencies import get_current_user_id
from .websocket_manager import manager
import json
from .rabbitmq import close_rabbitmq, publish_message_sent_event
from .schemas import UpdateSeenStatus
from typing import Optional
from .s3_upload import validate_and_upload
from .models import FileType
from .http_client import update_user_status



@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    print("Chat Service started")
    yield
    await close_rabbitmq()
    await engine.dispose()
    print("Chat Service stopped")


app = FastAPI(title="Chat Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/users/{user_id}")
async def get_users(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await crud.get_users(db, user_id)


@app.get("/messages/{sender}/{receiver}", response_model=schemas.ConversationResponse)

async def get_messages(
    sender: int,
    receiver: int,
    db: AsyncSession = Depends(get_db)
):
    return await crud.get_messages_between_users(db, sender, receiver)



@app.patch("/messages/unseen", status_code=200)
async def update_seen_status(
    # message_ids: list[int],
    payload: UpdateSeenStatus,
    db: AsyncSession = Depends(get_db),
   
):
    return await crud.update_messages_status(db, payload)


@app.post("/upload")
async def upload_file(
    file:       UploadFile           = File(...),
    caption:    Optional[str]        = Form(None),    # optional caption with file
    sender:     int                  = Form(...),
    receiver:   int                  = Form(...),
    _:          int                  = Depends(get_current_user_id)
):
    # upload file to S3
    result = await validate_and_upload(file)

    # save message to DB with both file and caption
    file_type_enum = FileType.IMAGE if result["file_type"] == "image" else FileType.VIDEO

    async with SessionLocal() as db:
        message = models.Message(
            caption   = caption or "",
            sender    = sender,
            receiver  = receiver,
            file      = result["url"],
            file_type = file_type_enum
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)

    payload = {
        "id":           message.id,
        "caption":      message.caption,
        "file":         message.file,
        "file_type":    "IMAGE" if result["file_type"] == "image" else "VIDEO",
        "file_name":    result["file_name"],
        "sender":       message.sender,
        "receiver":     message.receiver,
        "seen_flag":    message.seen_flag,
        "created_at":   str(message.created_at)
    }

    # deliver via WebSocket
    if message.sender in manager.active_connections:
        # await manager.active_connections[message.sender].send_json(payload)
        try:
            print(payload)
            await manager.active_connections[message.sender].send_json(payload)
        except Exception as e:
            print(f"Failed to send to sender back: {message.sender}: {e}")
            # remove dead connection
            if message.sender in manager.active_connections:
                del manager.active_connections[message.sender]
                await update_user_status(message.sender, "offline")
                print(f"Removed dead connection for user {message.sender}")

    # if message.receiver in manager.active_connections:
    #     await manager._safe_send(message.receiver, payload)
    if message.receiver in manager.active_connections:
        try: 
            await manager.active_connections[message.receiver].send_json(payload)
        except Exception as e:
            print(f"Failed to send to receiver back: {message.receiver}: {e}")
            # remove dead connection
            if message.receiver in manager.active_connections:
                del manager.active_connections[message.receiver]
                await update_user_status(message.receiver, "offline")
                print(f"Removed dead connection for user {message.receiver}")

    # publish to RabbitMQ for notification
    await publish_message_sent_event({
        "message_id":      message.id,
        "sender_id":       message.sender,
        "receiver_id":     message.receiver,
        "caption":         caption or "Sent a file",
        "receiver_online": message.receiver in manager.active_connections
    })

    return payload


@app.websocket("/ws/{client_id}/{email}")
async def websocket_endpoint(websocket: WebSocket, client_id: int, email: str):
    await manager.connect(websocket, email)
    try:
        while True:
            data    = await websocket.receive_text()
            parsed  = json.loads(data)

            if "changeStatus" in parsed:
                await manager.change_message_status(parsed)
            else:
                await manager.send_personal_message(parsed)

    except WebSocketDisconnect:
        await manager.disconnect(websocket)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "chat-service"}