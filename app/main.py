from fastapi import FastAPI , Query, Path, Body, Request, Depends,WebSocket,WebSocketDisconnect
from typing import Annotated, Literal
# from enum import Enum
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
import time
from sqlalchemy.orm import Session
from . import models, schemas, crud, database
import json
from typing import Dict



models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

# class ModelName(str, Enum):
#     alexnet = "alexnet"
#     resnet = "resnet"
#     lenet = "lenet"


# class FilterParams(BaseModel):
#     limit: int = Field(100, gt=0, le=100)
#     offset: int = Field(0, ge=0)
#     order_by: Literal["created_at", "updated_at"] = "created_at"
#     tags: list[str] = []


origins = [
    # "http://localhost.tiangolo.com",
    # "https://localhost.tiangolo.com",
    "http://localhost:3000",  # Next.js dev server
    "http://127.0.0.1:3000",

]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Dependency: get db session
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

from .websocket_realtime_chat import manager


@app.post("/api/users/signup", response_model=schemas.UserResponse,status_code=201)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    return crud.create_user(db, user)

@app.patch("/api/messages/unseen",status_code=200)
def create_user(user: list[int], db: Session = Depends(get_db)):
    return crud.updateMessagesStatus(db, user)


@app.post("/api/users/login", status_code=200)
def create_user(user: schemas.login, db: Session = Depends(get_db)):
    return crud.login(db, user)


@app.get("/api/users/{user}", response_model=Dict[int,schemas.AllUsersInfo],status_code=200)
def read_users(user,db: Session = Depends(get_db)):
    return crud.get_users(db,user)

@app.get("/api/messages/{sender}/{receiver}", response_model=schemas.receiverMessagesResponse,status_code=200)
def retrieve_messages(sender:int,receiver:int,db: Session = Depends(get_db)):
    print(sender,receiver)
    return crud.get_Messages_Send_Between_Two_Users(db,sender,receiver)


@app.websocket("/ws/{client_id}/{email}")
async def websocket_endpoint(websocket: WebSocket, client_id: int,email: str):
    print('this is received email: ',email)
    await manager.connect(websocket,email)
    
    try:
        while True:
            print('Loop runs')
            data = await websocket.receive_text()
            print('Hi buddy from the server')
            print(data)
            parsed = json.loads(data)
            # print( parsed["message"])
            # event = data.get("event")
            # msg = data.get("message")
            changeStatus='changeStatus'
            if changeStatus in parsed:
                manager.change_message_status(parsed)
            else:
                await manager.send_personal_message(parsed, websocket)
                await manager.broadcast(f"Client #{client_id} says: {parsed}")
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
        # await manager.broadcast(f"Client #{client_id} left the chat")

 # Example: {'event': 'chat', 'user': 123, 'message': 'Hello World!'}
            # event = data.get("event")
            # msg = data.get("message")

            # if event == "chat":
            #     await manager.broadcast(f"Client #{client_id} says: {msg}")