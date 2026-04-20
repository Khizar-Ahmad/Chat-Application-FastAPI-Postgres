import aio_pika
import json
import os
from dotenv import load_dotenv

load_dotenv()

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

connection = None
channel = None


async def get_rabbitmq_channel():
    global connection, channel
    if connection is None or connection.is_closed:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        channel = await connection.channel()
    return channel


async def publish_message_sent_event(payload: dict):
    try:
        ch = await get_rabbitmq_channel()

        # declare queue — creates it if it doesn't exist
        queue = await ch.declare_queue("message.sent", durable=True)

        await ch.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(payload).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT   
            ),
            routing_key="message.sent"
        )
        print(f"Event published to RabbitMQ: {payload}")

    except Exception as e:
        print(f"RabbitMQ publish failed: {e}")


async def close_rabbitmq():
    global connection
    if connection and not connection.is_closed:
        await connection.close()