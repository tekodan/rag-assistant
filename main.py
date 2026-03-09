"""
Application entry point — Open/Closed Principle (OCP).

Wires concrete implementations to their abstractions via lifespan.
To swap any service (e.g. ChromaDB → Qdrant), change only this file.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from core.config import settings
from repositories.chroma import ChromaVectorStore
from repositories.metrics import MetricsStore
from routers import chat, documents, metrics
from services.embedder import OllamaEmbedder
from services.llm import OllamaGenerator
from services.rag import RAGService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise services once on startup; inject into app.state for DI."""
    embedder = OllamaEmbedder(host=settings.ollama_host, model=settings.embed_model)
    vector_store = ChromaVectorStore(
        host=settings.chroma_host,
        port=settings.chroma_port,
        distance=settings.chroma_distance,
        collection_name=settings.chroma_collection,
    )
    generator = OllamaGenerator(
        host=settings.ollama_host,
        model=settings.chat_model,
        temperature=settings.llm_temperature,
        num_ctx=settings.llm_num_ctx,
        top_p=settings.llm_top_p,
        repeat_penalty=settings.llm_repeat_penalty,
    )

    app.state.embedder = embedder
    app.state.vector_store = vector_store
    app.state.metrics_store = MetricsStore(max_history=10)
    app.state.rag_service = RAGService(
        embedder=embedder,
        vector_store=vector_store,
        generator=generator,
        chat_model=settings.chat_model,
        similarity_threshold=settings.similarity_threshold,
        top_k=settings.retrieval_top_k,
        query_expansion=settings.query_expansion,
    )
    yield


app = FastAPI(
    title="RAG API",
    description="Document ingestion and question answering with local LLM via Ollama.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(metrics.router)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse("static/index.html")
