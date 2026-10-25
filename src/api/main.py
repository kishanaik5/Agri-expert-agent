from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from strawberry.fastapi import GraphQLRouter
from pydantic import BaseModel
import os
import threading

from src.api.schema import schema
from src.api.rate_limiter import RateLimitMiddleware, get_rate_limiter
from src.graph.client import get_graph_client
from src.queue.broker import init_broker_topology

# Initialize FastAPI App
app = FastAPI(
    title="Agri-Knowledge Graph Copilot API",
    description="Intelligent Multimodal Agricultural Advisory system powered by GraphQL, Neo4j, RabbitMQ, and LangGraph.",
    version="2.0.0"
)

# 1. Rate Limiting Middleware
app.add_middleware(RateLimitMiddleware)

# 2. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static & Frontend directories
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")

if os.path.exists(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Rate Limit Config Schema
class RateLimitConfigRequest(BaseModel):
    tier: str

@app.get("/api/ratelimit/status")
def get_ratelimit_status(request: Request):
    client_ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else "127.0.0.1")
    return get_rate_limiter().get_status(client_ip)

@app.post("/api/ratelimit/configure")
def configure_ratelimit(body: RateLimitConfigRequest, request: Request):
    client_ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else "127.0.0.1")
    ok = get_rate_limiter().set_client_tier(client_ip, body.tier)
    if not ok:
        return JSONResponse(status_code=400, content={"error": f"Invalid tier '{body.tier}'"})
    return get_rate_limiter().get_status(client_ip)

# Web UI routes
@app.get("/agri-ui", response_class=FileResponse)
@app.get("/ui", response_class=FileResponse)
def serve_ui():
    if os.path.exists(os.path.join(FRONTEND_DIST, "index.html")):
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

# GraphQL Router with GraphiQL Explorer
graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")

@app.get("/")
def root_endpoint():
    # If React frontend dist exists, serve it
    react_index = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(react_index):
        return FileResponse(react_index)
        
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    
    graph_ok = False
    try:
        graph_ok = get_graph_client().verify_connectivity()
    except Exception:
        pass

    return {
        "service": "Agri-Knowledge Graph Copilot API",
        "status": "healthy",
        "ui_endpoint": "/agri-ui",
        "graphql_endpoint": "/graphql",
        "rate_limiting": "/api/ratelimit/status",
        "neo4j_connected": graph_ok
    }

@app.get("/api/status")
def api_status():
    graph_ok = False
    try:
        graph_ok = get_graph_client().verify_connectivity()
    except Exception:
        pass

    return {
        "service": "Agri-Knowledge Graph Copilot API",
        "status": "healthy",
        "ui_endpoint": "/agri-ui",
        "graphql_endpoint": "/graphql",
        "neo4j_connected": graph_ok
    }

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
