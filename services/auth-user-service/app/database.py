from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv
import os

load_dotenv()

Base = declarative_base()


engine = None
SessionLocal = None


def get_engine():
    global engine
    if engine is None:
        DATABASE_URL = os.getenv("db_url")
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL is not set")
        engine = create_async_engine(DATABASE_URL, echo=True, pool_size=10, max_overflow=20)
    return engine


def get_session_local():
    global SessionLocal
    if SessionLocal is None:
        SessionLocal = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            class_=AsyncSession
        )
    return SessionLocal


async def get_db():
    async with get_session_local()() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise