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
            if db_user is not None:
                self.active_connections[db_user.id] = websocket
                db_user.connection_status='online'
                db_user.socket_id= email
                db_session.add(db_user)
                db_session.commit()
                db_session.refresh(db_user)
                print(db_user.connection_status)
                print('User connected Successfully!')
        finally:
            db_session.close()
        payload={"userId":db_user.id,"connectionNews":"user_connected","connection_status":"online"}
        await self.broadCastUserConnectionNews(payload)


    async def disconnect(self, websocket: WebSocket):
        db_session = SessionLocal()
        # db_user = models.User(socket_id=websocket)
        # if db_user is not None and  db_user.connection_status == 'online':
        print('Disconnect Handler')
        for key, value in list(self.active_connections.items()):  # use list() to avoid RuntimeError
            print('inside Loop disconnect:')
            if value == websocket:
                del self.active_connections[key]
                print(key)
                db_user = db_session.query(models.User).filter(models.User.id == key).first()  
                # my_dict.pop("x", None)
                print(db_user)
                db_user.connection_status='offline'
                db_user.socket_id= None
                db_session.add(db_user)
                db_session.commit()
                db_session.refresh(db_user)
                
                break



        # self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        print('Message in handler',message)
        db_session = SessionLocal()
        message = models.Message(caption=message["message"], sender=int(message["sender"]),receiver=int(message["receiver"]))
        db_session.add(message)
        db_session.commit()
        db_session.refresh(message)
        payload = {
        "id": message.id,
        "caption": message.caption,
        "sender": message.sender,
        "receiver": message.receiver,
        "seen_flag": message.seen_flag
        }
        if message.sender in self.active_connections:
            print('SenderId: ',message.sender)
            await self.active_connections[message.sender].send_json(payload)
            print('Message sent successfully: ',message.sender)

        if message.receiver in self.active_connections:
            print('ReceiverId: ',message.receiver)
            await self.active_connections[message.receiver].send_json(payload)
            print('Message sent successfully to Receiver: ',message.receiver)

            
        # await websocket.send_text(message)
    
    async def broadCastUserConnectionNews(self,message):
        for key,websocketId in self.active_connections.items():
            if message["userId"]==key:
                continue
            print('Connection News sent to user with id: ',key)
            await websocketId.send_json(message)

    async def broadcast(self, message: str):
        # for connection in self.active_connections:
        #     await connection.send_text(message)
        print('Broadcast',message)
    async def change_message_status(self,message):
        db_session = SessionLocal()
        message= db_session.query(models.Message).filter(models.Message.id == message.id).first()
        # message = models.Message(caption=message["message"], sender=int(message["sender"]),receiver=int(message["receiver"]))
        message.seen_flag=True
        db_session.add(message)
        db_session.commit()
        db_session.refresh(message)

manager = ConnectionManager()


