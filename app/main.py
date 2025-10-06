from fastapi import FastAPI , Query, Path, Body, Request, Depends,WebSocket,WebSocketDisconnect
from typing import Annotated, Literal
# from enum import Enum
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
import time
from sqlalchemy.orm import Session
from . import models, schemas, crud, database


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

@app.post("/api/users/login", status_code=200)
def create_user(user: schemas.login, db: Session = Depends(get_db)):
    return crud.login(db, user)

@app.get("/api/users/", response_model=list[schemas.UserResponse],status_code=200)
def read_users(db: Session = Depends(get_db)):
    return crud.get_users(db)

@app.websocket("/ws/{client_id}/{email}")
async def websocket_endpoint(websocket: WebSocket, client_id: int,email: str):
    print('this is received email: ',email)
    await manager.connect(websocket,email)
    
    try:
        while True:
            data = await websocket.receive_text()
                
            # event = data.get("event")
            # msg = data.get("message")
            await manager.send_personal_message(f"You wrote: {data}", websocket)
            await manager.broadcast(f"Client #{client_id} says: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        # await manager.broadcast(f"Client #{client_id} left the chat")

 # Example: {'event': 'chat', 'user': 123, 'message': 'Hello World!'}
            # event = data.get("event")
            # msg = data.get("message")

            # if event == "chat":
            #     await manager.broadcast(f"Client #{client_id} says: {msg}")