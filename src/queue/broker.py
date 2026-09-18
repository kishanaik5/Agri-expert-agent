import json
import socket
import pika
import uuid
from typing import Dict, Any, Optional
from src.config import (
    CLOUDAMQP_URL,
    RABBITMQ_HOST,
    RABBITMQ_PORT,
    RABBITMQ_USER,
    RABBITMQ_PASSWORD,
    RABBITMQ_EXCHANGE,
    RABBITMQ_QUEUE_DIAGNOSTICS,
    RABBITMQ_ROUTING_KEY_DIAGNOSTICS
)

def get_rabbitmq_connection() -> Optional[pika.BlockingConnection]:
    if CLOUDAMQP_URL:
        try:
            params = pika.URLParameters(CLOUDAMQP_URL)
            params.socket_timeout = 10
            params.heartbeat = 600
            params.blocked_connection_timeout = 300
            return pika.BlockingConnection(params)
        except Exception as e:
            print(f"[Broker] CloudAMQP connection error: {e}")
            return None

    # Local fallback
    try:
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
        parameters = pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            credentials=credentials,
            connection_attempts=3,
            retry_delay=2,
            heartbeat=600,
            blocked_connection_timeout=300
        )
        return pika.BlockingConnection(parameters)
    except Exception:
        return None

def init_broker_topology():
    """Declares exchange, queue, and bindings."""
    conn = get_rabbitmq_connection()
    if not conn:
        return False
    channel = conn.channel()
    
    # Declare Direct Exchange
    channel.exchange_declare(
        exchange=RABBITMQ_EXCHANGE,
        exchange_type="direct",
        durable=True
    )
    
    # Declare Diagnostics Queue
    channel.queue_declare(
        queue=RABBITMQ_QUEUE_DIAGNOSTICS,
        durable=True
    )
    
    # Bind Queue to Exchange
    channel.queue_bind(
        exchange=RABBITMQ_EXCHANGE,
        queue=RABBITMQ_QUEUE_DIAGNOSTICS,
        routing_key=RABBITMQ_ROUTING_KEY_DIAGNOSTICS
    )
    
    conn.close()
    print("[RabbitMQ] Topology initialized (Exchange & Queue bound).")
    return True

def publish_diagnostic_task(payload: Dict[str, Any], task_id: Optional[str] = None) -> str:
    """Publishes a diagnostic job into RabbitMQ / CloudAMQP."""
    task_id = task_id or f"task_{uuid.uuid4().hex[:12]}"
    message = {
        "task_id": task_id,
        "type": "crop_diagnostic_advisory",
        "payload": payload
    }
    
    conn = get_rabbitmq_connection()
    if not conn:
        raise ConnectionError("Message broker is not reachable.")

    channel = conn.channel()
    channel.basic_publish(
        exchange=RABBITMQ_EXCHANGE,
        routing_key=RABBITMQ_ROUTING_KEY_DIAGNOSTICS,
        body=json.dumps(message),
        properties=pika.BasicProperties(
            delivery_mode=2,  # make message persistent
            content_type="application/json"
        )
    )
    
    conn.close()
    return task_id
