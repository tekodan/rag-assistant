# DECISIONS.md — RAG Assistant

## Stack choices

| Decision        | Chosen           | Alternative      | Reason                                               |
|-----------------|------------------|------------------|------------------------------------------------------|
| LLM             | Ollama (local)   | OpenAI API       | No cost, no API keys, 100% private                   |
| Vector DB       | ChromaDB         | Qdrant / Pinecone| Fast setup, native Python client                     |
| API framework   | FastAPI          | Django / Flask   | Native async, automatic OpenAPI docs                 |
| PDF parser      | PyMuPDF          | pdfplumber       | Faster, extracts per-page metadata                   |
| Embeddings      | Ollama embed     | OpenAI embed     | Local, consistent with the main LLM                  |
| LLM model       | llama3.2:1b      | mistral / phi3   | Best quality/speed balance for local CPU inference   |

---

## What is implemented

### Core ✅
- Docker Compose with 3 services (`api`, `ollama`, `chromadb`)
- `POST /documents` — PDF ingestion with chunking and SHA-256 deduplication
- `POST /chat` — full RAG pipeline with source citations and rejection of out-of-context queries
- `GET /documents` / `DELETE /documents/{sha256}` — document CRUD
- `GET /metrics` — aggregate stats for the last 10 queries

### Quality & observability ✅
- Per-query metrics: response time, chunks retrieved/used, average distance, model name
- Similarity threshold to prevent hallucinations (cosine distance > threshold → reject)
- Query expansion support (disabled by default on CPU — saves ~3 Ollama calls per query)
- SSE streaming for `/chat` — first tokens appear in ~2-3 s instead of waiting for full response

### Tests ✅
- Integration tests via FastAPI `TestClient` with an isolated `test_documents` collection
- Unit tests for repository layer (`MetricsStore`, `ChromaVectorStore`) without HTTP overhead
- Session-scoped fixtures with automatic teardown — production data is never touched

### Frontend ✅
- Pico.css UI with Chat and Documents views
- Drag-and-drop PDF upload with progress bar
- Metrics panel below chat (per-query breakdown + aggregate chips)
- CSS and JS extracted into `static/assets/` (separate from HTML)

---

## Architecture decisions

### Repository pattern
Concrete data-access implementations (`ChromaVectorStore`, `MetricsStore`) live in
`repositories/`.  Protocols and domain dataclasses stay in `services/`.  This allows
swapping backends (e.g. Qdrant) by only changing `repositories/chroma.py` and the
wiring in `main.py`.

### SOLID principles
- **SRP** — each module has one job (routing, embedding, generation, storage, metrics).
- **OCP** — swap any backend by changing only `main.py` (composition root).
- **LSP** — concrete classes satisfy their protocols; tests can inject fakes.
- **ISP** — narrow protocols (`Embedder`, `Generator`, `VectorStore`) expose only what callers need.
- **DIP** — `RAGService` and routers depend on abstractions injected via `app.state`.

### Chunk size: 500 chars with 50-char overlap
Balance between embedding precision and sufficient context per chunk.
Overlap prevents information loss at chunk boundaries.

### Cosine distance
Changed from ChromaDB's default L2 to cosine so distance values are bounded [0, 1],
making the `SIMILARITY_THRESHOLD` parameter intuitive and portable across embedding models.
Auto-migration recreates the collection if the metric does not match.

### Static prompt template
Built by FastAPI with a fixed template, not generated dynamically by the LLM.
More predictable, faster, and cheaper — prompt construction is the engineer's job.

---

## What was left out and why

**Full RAGAS evaluation**
RAGAS requires OpenAI by default, adding external dependencies and cost.
Equivalent custom metrics (time, distance, rejection rate) cover the most important
production signals for a local MVP.

**Semantic re-ranking**
Improves retrieval quality but adds latency. The similarity threshold is sufficient
for the current scale.

**Auth / JWT**
Out of scope for the MVP. FastAPI middleware makes it straightforward to add later.

**Multi-role agents**
The modular architecture supports adding specialised agent endpoints that share the
same ChromaDB collection without touching existing code.

---

## Next iteration ideas

1. Full RAGAS evaluation using Ollama as the judge (no OpenAI dependency)
2. Cross-encoder re-ranking to improve retrieval precision
3. Async document ingestion queue (Celery + Redis) for large PDFs
4. Embedding cache for frequently queried documents
5. LangSmith or Langfuse for full chain observability
