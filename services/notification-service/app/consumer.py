import aio_pika
import json
import os
import asyncio
from dotenv import load_dotenv
from pathlib import Path
from .firebase import send_to_user_devices
from .database import get_session_local
from . import crud

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")


async def handle_message_sent(event: dict):
    receiver_id     = event.get("receiver_id")
    sender_id       = event.get("sender_id")
    caption         = event.get("caption", "New message")
    message_id      = event.get("message_id")
    receiver_online = event.get("receiver_online", False)

    # if receiver is online and got websocket delivery, skip push notification
    if receiver_online:
        print(f"Receiver {receiver_id} is online — skipping push notification")
        return

    # get receiver device tokens from DB
    async with get_session_local()() as db:
        devices = await crud.get_user_devices(db, receiver_id)

        if not devices:
            print(f"No devices registered for user {receiver_id}")
            return

        tokens = [d.token for d in devices]

        title = "New Message"
        body  = caption if caption else "You have a new message"

        # send FCM push notification
        await send_to_user_devices(tokens, title, body)

        # log it
        await crud.log_notification(
            db         = db,
            user_id    = receiver_id,
            message_id = message_id,
            title      = title,
            body       = body,
            is_sent    = True
        )


async def start_consumer():
    while True:
        try:
            print("Connecting to RabbitMQ...")
            connection = await aio_pika.connect_robust(RABBITMQ_URL)

            async with connection:
                channel = await connection.channel()
                await channel.set_qos(prefetch_count=10)

                queue = await channel.declare_queue("message.sent", durable=True)

                print("Notification Service listening on RabbitMQ queue: message.sent")

                async with queue.iterator() as queue_iter:
                    async for message in queue_iter:
                        async with message.process():
                            try:
                                event = json.loads(message.body.decode())
                                print(f"Received event: {event}")
                                await handle_message_sent(event)
                            except Exception as e:
                                print(f"Error processing message: {e}")

        except Exception as e:
            print(f"RabbitMQ connection lost: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)          # retry on connection failure