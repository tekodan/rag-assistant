# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.0.0] — 2026-03-10

### Added

#### Infrastructure
- Docker Compose stack with three services: `api` (FastAPI, port 8000), `chromadb` (port 8001), `ollama` (port 11435).
- `ollama-entrypoint.sh` that pulls `nomic-embed-text` and `llama3.2:1b` on first start.
- `Makefile` with targets: `up`, `down`, `restart`, `build`, `logs`, `logs-api`, `ps`, `clean`, `shell`.
- MIT `LICENSE` file.

#### API
- `POST /documents` — ingest a PDF: parse with PyMuPDF, chunk, embed via Ollama, store in ChromaDB. Returns chunk count and SHA-256 fingerprint.
- `GET /documents` — list all ingested documents with chunk count.
- `DELETE /documents/{sha256}` — remove a document and all its chunks from the vector store.
- `POST /chat` — RAG pipeline with SSE token-by-token streaming. Includes source citations (filename + page) and rejects queries when no relevant context is found.
- `GET /metrics` — aggregate statistics for the last 10 queries (response time, chunks retrieved/used, rejection rate, per-query history).

#### RAG pipeline
- Embedding via Ollama (`nomic-embed-text`).
- Cosine similarity search in ChromaDB with auto-migration if distance metric changes.
- Similarity threshold filtering to prevent hallucinations.
- Optional query expansion (3 semantic variants) — disabled by default on CPU.
- Source deduplication: unique (filename, page) pairs cited per answer.

#### Configuration
- All parameters configurable via environment variables: `CHROMA_*`, `OLLAMA_HOST`, `EMBED_MODEL`, `CHAT_MODEL`, `SIMILARITY_THRESHOLD`, `RETRIEVAL_TOP_K`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `QUERY_EXPANSION`, `LLM_TEMPERATURE`, `LLM_NUM_CTX`, `LLM_TOP_P`, `LLM_REPEAT_PENALTY`.
- Frozen `Settings` dataclass in `core/config.py`.

#### Architecture
- SOLID principles throughout: SRP (one module, one job), OCP (swap backends in `main.py` only), LSP (protocols), ISP (narrow interfaces), DIP (injection via `app.state`).
- **Repository layer** (`repositories/`): `ChromaVectorStore` and `MetricsStore` separated from protocol definitions.
- **Service layer** (`services/`): `Embedder`, `Generator`, `VectorStore` protocols + domain dataclasses. `RAGService` orchestrates the pipeline.
- **Router layer** (`routers/`): thin HTTP adapters for chat, documents, and metrics.
- **Core** (`core/`): settings only.

#### Frontend
- Single-page app using Pico.css (indigo theme).
- **Chat view**: SSE streaming, source citations, per-query metric bar below each answer.
- **Documents view**: drag-and-drop PDF upload with progress bar, document list with delete action.
- **Metrics panel** (collapsible): aggregate chips + per-query table.
- CSS and JS extracted into `static/assets/` (separate from `index.html`).

#### Tests
- Integration tests (`tests/test_api.py`) via FastAPI `TestClient` with an isolated `test_documents` ChromaDB collection — production data is never touched.
- Unit tests (`tests/test_repositories.py`) for `MetricsStore` and `ChromaVectorStore` directly, without going through the HTTP layer.
- Session-scoped fixtures with automatic teardown in `tests/conftest.py`.
- Tests covered: upload, duplicate rejection, non-PDF rejection, chat with context, empty query validation, document listing, metrics recording, out-of-context rejection.

#### Documentation
- `README.md` — setup, configuration reference, API table, test instructions, design principles.
- `DECISIONS.md` — stack choices, architecture decisions, and trade-offs (in English).
- `CHANGELOG.md` — this file.
