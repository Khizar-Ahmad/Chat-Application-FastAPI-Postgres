from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from contextlib import asynccontextmanager
from . import crud, schemas, models
# from .database import get_db, engine
from .database import get_db, get_engine
from .dependencies import get_current_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    print("Auth/User Service started")
    yield
    await get_engine().dispose()
    print("Auth/User Service stopped")


app = FastAPI(title="Auth/User Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/signup", response_model=schemas.UserResponse, status_code=201)
async def signup(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    val = await crud.create_user(db, user)
    val["detail"]= "Registered Successfully, Check OTP and verify your account"
    return val


@app.post("/login", response_model=schemas.LoginResponse, status_code=200)
async def login(credentials: schemas.UserLogin, db: AsyncSession = Depends(get_db)):
    return await crud.login(db, credentials)


@app.post("/refresh-token", response_model=schemas.RefreshResponse)
async def refresh_token(body: schemas.TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    return await crud.refresh_access_token(db, body.refresh_token)


@app.post("/logout")
async def logout(body: schemas.TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    return await crud.logout(db, body.refresh_token)


@app.get("/users/me", response_model=schemas.UserResponse)
async def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@app.get("/internal/users/{user_id}", response_model=schemas.InternalUserResponse)
async def get_user_by_id(user_id: int, db: AsyncSession = Depends(get_db)):
    return await crud.get_user_by_id(db, user_id)


@app.get("/internal/users/email/{email}", response_model=schemas.InternalUserResponse)
async def get_user_by_email(email: str, db: AsyncSession = Depends(get_db)):
    return await crud.get_user_by_email(db, email)


@app.get("/internal/users", response_model=list[schemas.InternalUserResponse])
async def get_all_users_internal(exclude_id: int, db: AsyncSession = Depends(get_db)):
    return await crud.get_all_users_except(db, exclude_id)


@app.patch("/internal/users/{user_id}/status")
async def update_status(
    user_id: int,
    body: schemas.UpdateConnectionStatus,
    db: AsyncSession = Depends(get_db)
):
    return await crud.update_connection_status(db, user_id, body.connection_status)

@app.post("/verify-otp")
async def verify_otp(
    payload: schemas.OTPVerifyRequest,
    db: AsyncSession = Depends(get_db)
):
    return await crud.verify_otp(db, payload)


@app.post("/resend-otp")
async def resend_otp(
    payload: schemas.ResendOTPRequest,
    db: AsyncSession = Depends(get_db)
):
    return await crud.resend_otp(db, payload)

@app.post("/forgot-password")
async def forgot_password(
    payload: schemas.ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    return await crud.forgot_password(db, payload)


@app.post("/reset-password")
async def reset_password(
    payload: schemas.ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    return await crud.reset_password(db, payload)

