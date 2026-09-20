from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter
from src.api.schema import schema
from src.graph.client import get_graph_client
from src.queue.broker import init_broker_topology

# Initialize FastAPI App
app = FastAPI(
    title="Agri-Knowledge Graph Copilot API",
    description="Intelligent Multimodal Agricultural Advisory system powered by GraphQL, Neo4j, RabbitMQ, and LangGraph.",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GraphQL Router with GraphiQL Explorer
graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")

@app.get("/")
def root_status():
    graph_ok = False
    try:
        graph_ok = get_graph_client().verify_connectivity()
    except Exception:
        pass

    return {
        "service": "Agri-Knowledge Graph Copilot API",
        "status": "healthy",
        "graphql_endpoint": "/graphql",
        "neo4j_connected": graph_ok
    }

import threading
import os

@app.on_event("startup")
def startup_event():
    try:
        init_broker_topology()
    except Exception as e:
        print(f"Warning: RabbitMQ topology init failed on startup: {e}")

    # Launch in-process consumer worker daemon for 100% free single-service hosting
    if os.getenv("ENABLE_WORKER_THREAD", "true").lower() in ("true", "1", "yes"):
        from src.queue.worker import start_worker
        worker_thread = threading.Thread(target=start_worker, daemon=True, name="AgriWorkerThread")
        worker_thread.start()
        print("[Startup] Launched background RabbitMQ LangGraph worker thread.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
