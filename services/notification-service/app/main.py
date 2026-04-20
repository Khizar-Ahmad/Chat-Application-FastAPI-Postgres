from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
import asyncio
from . import crud, schemas, models
from .database import get_db, get_engine
from .firebase import init_firebase
from .consumer import start_consumer


@asynccontextmanager
async def lifespan(app: FastAPI):
    # create tables
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

    init_firebase()

    consumer_task = asyncio.create_task(start_consumer())
    print("Notification Service started")

    yield

    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    await engine.dispose()
    print("Notification Service stopped")


app = FastAPI(title="Notification Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/register-device", response_model=schemas.DeviceResponse, status_code=201)
async def register_device(
    payload: schemas.RegisterDevice,
    db: AsyncSession = Depends(get_db)
):
    print(payload)
    return await crud.register_device(db, payload)


