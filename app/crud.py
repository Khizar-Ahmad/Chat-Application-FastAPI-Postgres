from sqlalchemy.orm import Session
from . import models, schemas
from .auth import get_password_hash,verify_password,create_access_token
from .models import User
from fastapi import HTTPException
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

def get_users(db: Session):
    return db.query(models.User).all()