"""
Chat router — Single Responsibility Principle (SRP).

POST /chat returns a Server-Sent Events stream so the user sees tokens
as they are generated instead of waiting for the full response.

SSE event types:
  {"type": "token",  "content": "..."}          — one per LLM token
  {"type": "done",   "sources": [], "metrics":{}}— end of stream, with metadata
  {"type": "reject", "answer": "...", "metrics":{}}— no relevant context found
"""

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from models.chat import ChatRequest, ChatResponse, QueryMetrics
from repositories.metrics import MetricsStore, QueryRecord
from services.rag import RAGService

router = APIRouter(prefix="/chat", tags=["Chat"])


# ── dependency providers ───────────────────────────────────────────────────────

def get_rag_service(request: Request) -> RAGService:
    return request.app.state.rag_service


def get_metrics_store(request: Request) -> MetricsStore:
    return request.app.state.metrics_store


# ── endpoint ───────────────────────────────────────────────────────────────────

@router.post("")
async def chat(
    body: ChatRequest,
    rag: RAGService = Depends(get_rag_service),
    metrics_store: MetricsStore = Depends(get_metrics_store),
) -> StreamingResponse:
    """
    Answer a question using RAG with token-by-token streaming (SSE).

    The client receives tokens as they are generated; final metadata
    (sources, metrics) is sent in the last `done` or `reject` event.
    """
    async def event_stream() -> AsyncIterator[str]:
        last_event: dict | None = None

        async for line in rag.answer_stream(body.query, top_k=body.n_results):
            yield line
            # Parse the last SSE line to extract metadata for MetricsStore
            if line.startswith("data:"):
                import json
                try:
                    last_event = json.loads(line[5:].strip())
                except Exception:
                    pass

        # Record metrics after stream completes
        if last_event and last_event.get("type") in ("done", "reject"):
            m = last_event.get("metrics", {})
            metrics_store.record(QueryRecord(
                tiempo_respuesta=m.get("tiempo_respuesta", 0),
                chunks_encontrados=m.get("chunks_encontrados", 0),
                chunks_usados=m.get("chunks_usados", 0),
                distancia_promedio=m.get("distancia_promedio"),
                modelo_usado=m.get("modelo_usado", ""),
                rechazada=last_event.get("type") == "reject",
            ))

    return StreamingResponse(event_stream(), media_type="text/event-stream")
