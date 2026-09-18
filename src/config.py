import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# Load .env
load_dotenv(BASE_DIR / ".env")

# Neo4j Cloud / Local Settings
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME") or os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "agri_password123")

# RabbitMQ / CloudAMQP Settings
CLOUDAMQP_URL = os.getenv("CLOUDAMQP_URL")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "agri_user")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "agri_pass123")

RABBITMQ_EXCHANGE = "agri.tasks.exchange"
RABBITMQ_QUEUE_DIAGNOSTICS = "agri.queue.diagnostics"
RABBITMQ_ROUTING_KEY_DIAGNOSTICS = "agri.task.diagnostic"

# API Settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("PORT", os.getenv("API_PORT", "8000")))
