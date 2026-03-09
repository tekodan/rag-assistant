"""
RAG orchestration service — Single Responsibility Principle (SRP).

Responsible solely for the retrieval-augmented generation pipeline:
  1. Query expansion   → improve recall with semantic variants
  2. Retrieval         → embed + search in vector store
  3. Similarity filter → discard irrelevant chunks (avoid hallucinations)
  4. Generation        → build grounded answer with source citations
"""

import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass

from services.embedder import Embedder
from services.llm import Generator
from services.vector_store import SearchResult, VectorStore

_EXPANSION_SYSTEM = (
    "Generate 3 alternative phrasings of the following question to improve document search. "
    "Return only the 3 questions, one per line, no numbering or extra text."
)

_ANSWER_SYSTEM = (
    "You are a helpful assistant that answers questions based exclusively on the provided "
    "document context. If the context is insufficient, say so explicitly. "
    "Always cite your sources using the format [filename, p.N]."
)


@dataclass
class RAGResponse:
    answer: str
    sources: list[dict]
    tiempo_respuesta: float
    chunks_encontrados: int
    chunks_usados: int
    distancia_promedio: float | None
    modelo_usado: str
    rechazada: bool


class RAGService:
    """
    Orchestrates query expansion, retrieval, filtering, and generation.

    Dependencies are injected via constructor (Dependency Inversion Principle),
    so each component (Embedder, VectorStore, Generator) is replaceable.
    """

    def __init__(
        self,
        embedder: Embedder,
        vector_store: VectorStore,
        generator: Generator,
        chat_model: str,
        similarity_threshold: float = 0.8,
        top_k: int = 5,
        query_expansion: bool = False,
    ) -> None:
        self._embedder = embedder
        self._vector_store = vector_store
        self._generator = generator
        self._chat_model = chat_model
        self._similarity_threshold = similarity_threshold
        self._top_k = top_k
        self._query_expansion = query_expansion

    async def answer(self, query: str, top_k: int | None = None) -> RAGResponse:
        k = top_k or self._top_k
        start = time.perf_counter()

        # 1. Optionally expand query into semantic variants to improve recall
        # Disabled by default on CPU — each expansion adds ~60-90s on llama3.2:1b
        variants = await self._expand_query(query) if self._query_expansion else []
        queries = [query] + variants

        # 2. Embed each variant and retrieve candidates, deduplicating by chunk_id
        seen: set[str] = set()
        candidates: list[SearchResult] = []
        for q in queries:
            embedding = await self._embedder.embed(q)
            for result in self._vector_store.query(embedding, k):
                if result.chunk_id not in seen:
                    seen.add(result.chunk_id)
                    candidates.append(result)

        # 3. Filter by similarity threshold to avoid hallucinations
        relevant = [r for r in candidates if r.distance <= self._similarity_threshold]

        elapsed = round(time.perf_counter() - start, 3)

        if not relevant:
            return RAGResponse(
                answer="No encontré información relevante en los documentos para responder esta pregunta.",
                sources=[],
                tiempo_respuesta=elapsed,
                chunks_encontrados=len(candidates),
                chunks_usados=0,
                distancia_promedio=None,
                modelo_usado=self._chat_model,
                rechazada=True,
            )

        # 4. Build context and generate grounded answer
        context = self._build_context(relevant)
        answer = await self._generator.generate(
            system=_ANSWER_SYSTEM,
            user=f"Context:\n{context}\n\nQuestion: {query}",
        )

        elapsed = round(time.perf_counter() - start, 3)
        avg_distance = round(sum(r.distance for r in relevant) / len(relevant), 4)

        return RAGResponse(
            answer=answer,
            sources=self._unique_sources(relevant),
            tiempo_respuesta=elapsed,
            chunks_encontrados=len(candidates),
            chunks_usados=len(relevant),
            distancia_promedio=avg_distance,
            modelo_usado=self._chat_model,
            rechazada=False,
        )

    async def answer_stream(
        self, query: str, top_k: int | None = None
    ) -> AsyncIterator[str]:
        """
        Streaming variant of answer().
        Yields SSE-formatted lines:
          data: {"type": "token",  "content": "..."}   — one per LLM token
          data: {"type": "done",   "sources": [...], "metrics": {...}}
          data: {"type": "reject", "answer": "...", "metrics": {...}}
        """
        k = top_k or self._top_k
        start = time.perf_counter()

        variants = await self._expand_query(query) if self._query_expansion else []
        queries = [query] + variants

        seen: set[str] = set()
        candidates: list[SearchResult] = []
        for q in queries:
            embedding = await self._embedder.embed(q)
            for result in self._vector_store.query(embedding, k):
                if result.chunk_id not in seen:
                    seen.add(result.chunk_id)
                    candidates.append(result)

        relevant = [r for r in candidates if r.distance <= self._similarity_threshold]
        elapsed_retrieval = round(time.perf_counter() - start, 3)

        if not relevant:
            payload = json.dumps({
                "type": "reject",
                "answer": "No encontré información relevante en los documentos para responder esta pregunta.",
                "sources": [],
                "metrics": {
                    "tiempo_respuesta": elapsed_retrieval,
                    "chunks_encontrados": len(candidates),
                    "chunks_usados": 0,
                    "distancia_promedio": None,
                    "modelo_usado": self._chat_model,
                },
            })
            yield f"data: {payload}\n\n"
            return

        context = self._build_context(relevant)
        full_answer = []

        async for token in self._generator.stream(
            system=_ANSWER_SYSTEM,
            user=f"Context:\n{context}\n\nQuestion: {query}",
        ):
            full_answer.append(token)
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

        elapsed = round(time.perf_counter() - start, 3)
        avg_distance = round(sum(r.distance for r in relevant) / len(relevant), 4)

        done_payload = json.dumps({
            "type": "done",
            "sources": self._unique_sources(relevant),
            "metrics": {
                "tiempo_respuesta": elapsed,
                "chunks_encontrados": len(candidates),
                "chunks_usados": len(relevant),
                "distancia_promedio": avg_distance,
                "modelo_usado": self._chat_model,
            },
        })
        yield f"data: {done_payload}\n\n"

    # ── private helpers ────────────────────────────────────────────────────────

    async def _expand_query(self, query: str) -> list[str]:
        """Ask the LLM for 3 semantic variants of the query. Fails silently."""
        try:
            raw = await self._generator.generate(system=_EXPANSION_SYSTEM, user=query)
            return [line.strip() for line in raw.strip().splitlines() if line.strip()][:3]
        except Exception:
            return []

    def _build_context(self, results: list[SearchResult]) -> str:
        parts = []
        for r in results:
            archivo = r.metadata.get("archivo", "unknown")
            pagina = r.metadata.get("pagina", "?")
            parts.append(f"[{archivo}, p.{pagina}]\n{r.document}")
        return "\n\n".join(parts)

    def _unique_sources(self, results: list[SearchResult]) -> list[dict]:
        seen: set[tuple] = set()
        sources = []
        for r in results:
            key = (r.metadata.get("archivo"), r.metadata.get("pagina"))
            if key not in seen:
                seen.add(key)
                sources.append({"archivo": key[0], "pagina": key[1]})
        return sources
