
import httpx
from fastapi import FastAPI, Request, WebSocket, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os
import websockets
import json

load_dotenv()

AUTH_SERVICE         = os.getenv("AUTH_SERVICE_URL", "http://127.0.0.1:8001")
CHAT_SERVICE         = os.getenv("CHAT_SERVICE_URL", "http://127.0.0.1:8002")
NOTIFICATION_SERVICE = os.getenv("NOTIFICATION_SERVICE_URL", "http://127.0.0.1:8003")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("API Gateway started")
    yield
    print("API Gateway stopped")


app = FastAPI(title="API Gateway", lifespan=lifespan)

origins = [
    # "http://localhost.tiangolo.com",
    # "https://localhost.tiangolo.com",
    "http://localhost:3000",  # Next.js dev server
    "http://127.0.0.1:3000",
    "https://chat-application-by-khizarahmad.netlify.app",
    "http://chat-application-by-khizarahmad.netlify.app"
    # "http://localhost:8001",
    # "http://localhost:8002",
    # "http://localhost:8003"

]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



async def proxy(request: Request, url: str):
    async with httpx.AsyncClient(timeout=30) as client:
        # forward same method, headers, body
        response = await client.request(
            method  = request.method,
            url     = url,
            headers = {
                key: value for key, value in request.headers.items()
                if key.lower() not in ["host", "content-length"]
            },
            content = await request.body(),
            params  = request.query_params
        )
        return JSONResponse(
            content     = response.json(),
            status_code = response.status_code
        )



@app.post("/api/users/signup")
async def signup(request: Request):
    return await proxy(request, f"{AUTH_SERVICE}/signup")


@app.post("/api/users/login")
async def login(request: Request):
    return await proxy(request, f"{AUTH_SERVICE}/login")


@app.post("/api/users/refresh-token")
async def refresh_token(request: Request):
    return await proxy(request, f"{AUTH_SERVICE}/refresh-token")


@app.post("/api/users/logout")
async def logout(request: Request):
    return await proxy(request, f"{AUTH_SERVICE}/logout")


@app.get("/api/users/me")
async def get_me(request: Request):
    return await proxy(request, f"{AUTH_SERVICE}/users/me")


@app.get("/api/users/{user_id}")
async def get_users(user_id: int, request: Request):
    return await proxy(request, f"{CHAT_SERVICE}/users/{user_id}")


@app.get("/api/messages/{sender}/{receiver}")
async def get_messages(sender: int, receiver: int, request: Request):
    return await proxy(request, f"{CHAT_SERVICE}/messages/{sender}/{receiver}")


@app.patch("/api/messages/unseen")
async def update_seen_status(request: Request):
    return await proxy(request, f"{CHAT_SERVICE}/messages/unseen")




@app.get("/api/send/email/{user}")
async def send_email(user: str, request: Request):
    return await proxy(request, f"{NOTIFICATION_SERVICE}/send/email/{user}")


@app.get("/api/task-status/{task_id}")
async def task_status(task_id: str, request: Request):
    return await proxy(request, f"{NOTIFICATION_SERVICE}/task-status/{task_id}")

@app.post("/api/notifications/register-device")
async def register_device(request: Request):
    return await proxy(request, f"{NOTIFICATION_SERVICE}/register-device")
# ── WebSocket Proxy ───────────────────────────────────────────
# WebSocket cannot use httpx — needs its own proxying logic

@app.post("/api/users/verify-otp")
async def verify_otp(request: Request):
    return await proxy(request, f"{AUTH_SERVICE}/verify-otp")

@app.post("/api/users/resend-otp")
async def resend_otp(request: Request):
    return await proxy(request, f"{AUTH_SERVICE}/resend-otp")
    
@app.post("/api/users/forgot-password")
async def forgot_password(request: Request):
    return await proxy(request, f"{AUTH_SERVICE}/forgot-password")


@app.post("/api/users/reset-password")
async def reset_password(request: Request):
    return await proxy(request, f"{AUTH_SERVICE}/reset-password")

@app.post("/api/upload")
async def upload_file(request: Request):
    async with httpx.AsyncClient(timeout=120) as client:
        body    = await request.body()
        headers = {
            key: value for key, value in request.headers.items()
            if key.lower() not in ["host", "content-length"]
        }
        response = await client.post(
            f"{CHAT_SERVICE}/upload",
            content = body,
            headers = headers
        )

    # handle empty or non-JSON responses safely
    try:
        content = response.json()
    except Exception:
        content = {"detail": "Upload failed"}

    return JSONResponse(
        content     = content,
        status_code = response.status_code
    )
    

@app.websocket("/ws/{client_id}/{email}")
async def websocket_proxy(websocket: WebSocket, client_id: int, email: str):
    await websocket.accept()

    # connect to Chat Service WebSocket
    chat_ws_url = f"{CHAT_SERVICE.replace('http', 'ws')}/ws/{client_id}/{email}"

    try:
        async with websockets.connect(chat_ws_url) as chat_ws:
            import asyncio

            # forward messages from frontend → chat service
            async def forward_to_chat():
                try:
                    while True:
                        data = await websocket.receive_text()
                        await chat_ws.send(data)
                except Exception:
                    pass

            # forward messages from chat service → frontend
            async def forward_to_client():
                try:
                    async for message in chat_ws:
                        await websocket.send_text(message)
                except Exception:
                    pass
                
            task1 = asyncio.create_task(forward_to_chat())
            task2 = asyncio.create_task(forward_to_client())

            # wait for EITHER task to finish
            done, pending = await asyncio.wait(
                [task1, task2],
                return_when=asyncio.FIRST_COMPLETED   # ← key line
            )

            # cancel the other task immediately
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # explicitly close chat service websocket
            # this triggers disconnect handler in chat service
            try:
                await chat_ws.close()
            except Exception:
                pass

    except Exception as e:
        print(f"WebSocket proxy error: {e}")
    finally:
        try:
            if websocket.client_state.value == 1:
                await websocket.close()
        except Exception:
            pass



