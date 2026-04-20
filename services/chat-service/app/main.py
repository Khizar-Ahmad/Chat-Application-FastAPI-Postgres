from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from . import crud, schemas, models
from .database import get_db, engine
from .dependencies import get_current_user_id
from .websocket_manager import manager
import json
from .rabbitmq import close_rabbitmq


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
    message_ids: list[int],
    db: AsyncSession = Depends(get_db),
   
):
    return await crud.update_messages_status(db, message_ids)


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