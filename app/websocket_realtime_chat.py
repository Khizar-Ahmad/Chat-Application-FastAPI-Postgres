from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from .database import SessionLocal
from . import models, schemas
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str,WebSocket] = {}

    async def connect(self, websocket: WebSocket,email:str):
        await websocket.accept()
        print(email)
        db_session = SessionLocal()
        # db_user = models.User(email=email)
        try:

            db_user = db_session.query(models.User).filter(models.User.email == email).first()

            print(db_user.connection_status)
            if db_user is not None and db_user.connection_status == 'offline':
                self.active_connections[email] = websocket
                db_user.connection_status='online'
                db_user.socket_id= email
                db_session.add(db_user)
                db_session.commit()
                db_session.refresh(db_user)
                print(db_user.connection_status)
                print('User connected Successfully!')
        finally:
            db_session.close()


    def disconnect(self, websocket: WebSocket):
        db_session = SessionLocal()
        # db_user = models.User(socket_id=websocket)
        # if db_user is not None and  db_user.connection_status == 'online':
        for key, value in list(self.active_connections.items()):  # use list() to avoid RuntimeError
            if value == websocket:
                del self.active_connections[key]
                print(key)
                db_user = db_session.query(models.User).filter(models.User.email == key).first()  
                # my_dict.pop("x", None)
                db_user.connection_status='offline'
                db_user.socket_id= None
                db_session.add(db_user)
                db_session.commit()
                db_session.refresh(db_user)
                break



        # self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()


