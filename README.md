# Agri-Expert Agent: Multimodal Agricultural Knowledge Graph Copilot

An intelligent, multi-step agricultural advisory system combining **Strawberry GraphQL**, **LangGraph**, **RabbitMQ**, and **Neo4j Knowledge Graph**.

---

## 🏗 System Architecture

```
                 ┌─────────────────────────────────────────────────────────┐
                 │            Client (GraphiQL / Web App / API)            │
                 │                 http://localhost:8000/graphql           │
                 └────────────────────────────┬────────────────────────────┘
                                              │
                     GraphQL Query / Mutation │
                                              ▼
                 ┌─────────────────────────────────────────────────────────┐
                 │         FastAPI + Strawberry GraphQL API Server         │
                 │  - Queries: crops, cropDetails, disease, zoneRecs       │
                 │  - Mutations: submitDiagnosticTask, instantAdvisory     │
                 └──────────────┬───────────────────────────┬──────────────┘
     Fast Direct Queries        │                           │ Task Dispatch
     (Profile / Ontologies)     │                           │ (Background Queue)
                                ▼                           ▼
                 ┌──────────────────────────┐    ┌──────────────────────────┐
                 │  Neo4j Knowledge Graph   │    │  RabbitMQ Message Broker │
                 │  (Nodes: Crop, Disease,  │    │  (Queue: agri.tasks)     │
                 │   Stage, Pathogen, Zone) │    └───────────┬──────────────┘
                 └──────────────▲───────────┘                │
                                │                            │ Consume Task
                                │ Graph Traversal            ▼
                                │ Multi-hop Context ┌────────────────────────┐
                                └───────────────────┤  LangGraph AI Worker   │
                                                    │   (Multi-Step Engine)  │
                                                    └────────────────────────┘
```

---

## 🚀 Key Features

* **Neo4j Knowledge Graph:** Connected ontology spanning Crops, Growth Phases, Pathogens, Treatments (Chemical & Biological), Agro-Climatic Zones, and Soil Suitability.
* **LangGraph Multi-Agent Engine:** Multi-step deterministic and LLM-assisted graph reasoning (`extract_entities` $\rightarrow$ `traverse_graph` $\rightarrow$ `synthesize_advisory`).
* **RabbitMQ Message Broker:** Decoupled task queue for handling asynchronous, resilient background diagnostic processing.
* **Strawberry GraphQL API:** Strongly typed, flexible API with interactive GraphiQL playground.
* **Zero-Downtime Hybrid Fallback:** Built-in in-memory knowledge engine guaranteeing continuous offline development and instantaneous fallback.

---

## 📦 Quickstart

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your Neo4j (Local or AuraDB) and RabbitMQ (Local or CloudAMQP) credentials:
```bash
cp .env.example .env
```

### 3. Seed Knowledge Graph
```bash
python -m src.graph.ingest
```

### 4. Start API Server
```bash
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```
Open **[http://localhost:8000/graphql](http://localhost:8000/graphql)** for the interactive GraphiQL IDE.

### 5. Start RabbitMQ Background Worker
```bash
python -m src.queue.worker
```

---

## 🔍 Sample GraphQL Queries

### Query Crop Diseases & Treatments
```graphql
query {
  disease(crop: "Cotton", symptoms: "Leaf Blight") {
    crop
    disease
    pathogen
    treatments
  }
}
```

### Query Regional Agro-Climatic Suitability by PIN Code
```graphql
query {
  zoneRecommendations(pincode: "141004", soilClass: 2) {
    crop
    zoneId
    combinedScore
  }
}
```

### Submit Asynchronous Diagnostic Advisory Task
```graphql
mutation {
  submitDiagnosticTask(
    cropName: "Wheat",
    symptoms: "Yellow stripe rust",
    pincode: "141004"
  ) {
    taskId
    status
    message
  }
}
```

---

## ☁️ Deployment

* **Render.com:** Pre-configured with `render.yaml` for 1-click free tier deployment.
* **Docker:** Multi-stage `Dockerfile` included for containerized hosting.
