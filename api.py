"""FastAPI backend exposing the GraphRAG engine over HTTP.

The engine is expensive to build (embedding probe, cross-encoder reranker,
Neo4j/Qdrant/Ollama connections), so it is constructed ONCE at startup via the
lifespan handler and reused across every request.
"""

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config.app_config_loader import load_app_config
from app.config.graph_schema_loader import load_graph_schema
from main import build_engine  # reuse the exact wiring the CLI already uses


# --- Request / Response shapes -------------------------------------------

class QueryRequest(BaseModel):
    query: str
    limit: int = 5


class SourceChunk(BaseModel):
    id: str
    document_id: str
    text: str


class SourceFact(BaseModel):
    source: str
    relationship_type: str
    target: str
    description: str | None = None


class QueryResponse(BaseModel):
    query: str
    answer: str
    chunks: list[SourceChunk]
    facts: list[SourceFact]


# --- Engine lifecycle: build ONCE at startup -----------------------------

engine = {}  # holder populated during lifespan, read in the route


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv()
    config = load_app_config("config/app.yaml")
    schema = load_graph_schema("config/graph.yaml")
    engine["instance"] = build_engine(config, schema)
    yield
    engine.clear()


app = FastAPI(title="GraphRAG API", lifespan=lifespan)

# Allow the Streamlit frontend (a different origin/port) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "engine_ready": "instance" in engine}


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    result = engine["instance"].query(request.query, limit=request.limit)
    return QueryResponse(
        query=result.query,
        answer=result.answer,
        chunks=[
            SourceChunk(id=c.id, document_id=c.document_id, text=c.text)
            for c in result.chunks
        ],
        facts=[
            SourceFact(
                source=f.source,
                relationship_type=f.relationship_type,
                target=f.target,
                description=f.description,
            )
            for f in result.facts
        ],
    )
