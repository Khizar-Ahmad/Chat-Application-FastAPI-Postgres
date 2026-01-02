from sqlalchemy.orm import Session
from . import models, schemas
from .auth import get_password_hash,verify_password,create_access_token
from .models import User
from fastapi import HTTPException
from sqlalchemy import or_, and_
def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(name=user.name, email=user.email,password=user.password)
    hashedPassword=get_password_hash(db_user.password)
    db_user.password= hashedPassword
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
def login(db: Session, user: schemas.login):
    db_user = models.User(email=user.email,password=user.password)
    # hashedPassword=get_password_hash(db_user.password)
    userInstance = db.query(User).filter(User.email == db_user.email).first()
    if userInstance is None:
        raise HTTPException(status_code=404, detail="User not found")
    flag=verify_password(user.password,userInstance.password)
    print(flag)
    if flag is not True:
        raise HTTPException(status_code=400, detail="Invalid email or password")
    # db_user.password= hashedPassword
    # db.add(db_user)
    # db.commit()
    # db.refresh(db_user)
    payload={}
    # payload["id"]=userInstance.id
    # payload["name"]=userInstance.name
    # payload["email"]=userInstance.email
    payload.update({"id":userInstance.id,"name":userInstance.name,"email":userInstance.email})
    return {"user":payload,"token":create_access_token(payload)}

def get_users(db: Session,user):
    users=db.query(models.User).filter(models.User.id != user).all()
    d = { item.id:{"userInfo":item,"data":[]} for ind,item in enumerate(users)}
    messages = (
    db.query(models.Message)
    .filter(
        models.Message.receiver == user,
        models.Message.seen_flag == False
    )
    .all()
    )
    for item in messages:
        if item.sender in d:
            d[item.sender]["data"].append(item)
    return d

def get_Messages_Send_Between_Two_Users(db: Session,sender,receiver):

    allMessages= db.query(models.Message).filter(
        or_(
            and_(models.Message.sender == sender, models.Message.receiver == receiver),
            and_(models.Message.sender == receiver, models.Message.receiver == sender)
        )
    ).all()
    print(receiver,type(receiver))
    userInstance = db.query(User).filter(User.id == receiver).first()

    if not userInstance:
        return {
            "error": "Receiver not found",
            "data": []
        }
    
    resPayload = {
    "userInfo": {
        "id":userInstance.id,
        "name": userInstance.name,
        "email": userInstance.email,
        "connection_status": userInstance.connection_status,
    },
    "data": [msg for msg in allMessages],
    }
    return resPayload
def updateMessagesStatus(db:Session,unSeenMessages):
    messages = (
    db.query(models.Message)
    .filter(models.Message.id.in_(unSeenMessages))
    .update(
        {models.Message.seen_flag: True},
        synchronize_session=False
    )
    )
    db.commit()
    return {"status":"success","message":"messages status updated successfully"}
