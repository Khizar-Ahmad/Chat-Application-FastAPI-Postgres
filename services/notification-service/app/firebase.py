import firebase_admin
from firebase_admin import credentials, messaging
from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

CREDENTIALS_PATH = os.getenv(
    "FIREBASE_CREDENTIALS_PATH",
    "firebase-service-account.json"
)

# initialize once at startup
_firebase_app = None


def init_firebase():
    global _firebase_app
    if not firebase_admin._apps:
        cred = credentials.Certificate(CREDENTIALS_PATH)
        _firebase_app = firebase_admin.initialize_app(cred)
        print("Firebase initialized")


async def send_push_notification(token: str, title: str, body: str) -> tuple[bool, str]:
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            token=token,
        )
        response = messaging.send(message)
        print(f"FCM sent successfully: {response}")
        return True, None

    except Exception as e:
        print(f"FCM send failed: {e}")
        return False, str(e)


async def send_to_user_devices(tokens: list[str], title: str, body: str) -> None:
    for token in tokens:
        success, error = await send_push_notification(token, title, body)
        if not success:
            print(f"Failed for token {token[:20]}...: {error}")