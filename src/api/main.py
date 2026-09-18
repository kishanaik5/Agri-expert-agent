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

@app.on_event("startup")
def startup_event():
    try:
        init_broker_topology()
    except Exception as e:
        print(f"Warning: RabbitMQ topology init failed on startup: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
