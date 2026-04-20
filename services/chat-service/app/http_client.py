import httpx
from fastapi import HTTPException
from dotenv import load_dotenv
import os

load_dotenv()

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL")


async def get_user_by_id(user_id: int) -> dict:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{AUTH_SERVICE_URL}/internal/users/{user_id}")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Auth service unavailable")


async def get_user_by_email(email: str) -> dict:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{AUTH_SERVICE_URL}/internal/users/email/{email}")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Auth service unavailable")


async def get_all_users_except(user_id: int) -> list[dict]:
    async with httpx.AsyncClient() as client:
        try:
            
            response = await client.get(
                f"{AUTH_SERVICE_URL}/internal/users",
                params={"exclude_id": user_id}
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Auth service unavailable")


async def update_user_status(user_id: int, status: str) -> None:
    async with httpx.AsyncClient() as client:
        try:
            await client.patch(
                f"{AUTH_SERVICE_URL}/internal/users/{user_id}/status",
                json={"user_id": user_id, "connection_status": status}
            )
        except httpx.RequestError:
            print(f"Warning: could not update status for user {user_id}")