# RAG Assistant

A local Retrieval-Augmented Generation (RAG) system built with **FastAPI**, **ChromaDB**, and **Ollama**. Upload PDF documents and ask questions — answers are grounded exclusively in your documents, with no data leaving your machine.

## Getting started

```bash
make up
```

Then open **http://localhost:8000** in your browser.

> First run downloads the Ollama models (`nomic-embed-text` and `llama3.2:1b`) — this may take a few minutes depending on your connection.

---

## Architecture

Three services orchestrated via Docker Compose:

| Service   | Port (host) | Role                              |
|-----------|-------------|-----------------------------------|
| `api`     | 8000        | FastAPI — ingestion & chat        |
| `chromadb`| 8001        | Vector store (cosine similarity)  |
| `ollama`  | 11435       | Local LLM inference               |

### Data flow

```
POST /documents  →  parse PDF (PyMuPDF)  →  embed (Ollama)  →  store (ChromaDB)
POST /chat       →  embed query          →  similarity search →  generate (Ollama, SSE)
```

### Project layout

```
.
├── core/
│   └── config.py           # All settings from env vars
├── models/
│   ├── chat.py             # Pydantic request/response models
│   └── documents.py
├── repositories/
│   ├── chroma.py           # ChromaVectorStore (concrete implementation)
│   └── metrics.py          # MetricsStore + QueryRecord
├── routers/
│   ├── chat.py             # POST /chat  (SSE streaming)
│   ├── documents.py        # CRUD /documents
│   └── metrics.py          # GET /metrics
├── services/
│   ├── embedder.py         # Embedder protocol + OllamaEmbedder
│   ├── llm.py              # Generator protocol + OllamaGenerator
│   ├── rag.py              # RAGService — orchestration pipeline
│   └── vector_store.py     # VectorStore protocol + domain dataclasses
├── static/
│   ├── index.html
│   └── assets/
│       ├── app.js
│       └── style.css
├── tests/
│   ├── conftest.py         # Fixtures (client, repos, test PDF)
│   ├── test_api.py         # Integration tests (HTTP layer)
│   └── test_repositories.py# Unit tests (repository layer)
├── docker-compose.yml
├── Dockerfile
└── main.py                 # App factory + DI wiring
```

---

## Quick start

### With Docker (recommended)

```bash
docker compose up --build
```

Open [http://localhost:8000](http://localhost:8000).

### Locally (without Docker)

Requires ChromaDB and Ollama running separately.

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

---

## Configuration

All parameters are set via environment variables (see `docker-compose.yml`):

| Variable              | Default              | Purpose                              |
|-----------------------|----------------------|--------------------------------------|
| `CHROMA_HOST`         | `chromadb`           | ChromaDB hostname                    |
| `CHROMA_PORT`         | `8000`               | ChromaDB port (internal)             |
| `CHROMA_DISTANCE`     | `cosine`             | Distance metric (`cosine` or `l2`)   |
| `CHROMA_COLLECTION`   | `documents`          | Collection name                      |
| `OLLAMA_HOST`         | `http://ollama:11434`| Ollama base URL                      |
| `EMBED_MODEL`         | `nomic-embed-text`   | Embedding model                      |
| `CHAT_MODEL`          | `llama3.2:1b`        | Chat/generation model                |
| `SIMILARITY_THRESHOLD`| `0.5`                | Max cosine distance to keep a chunk  |
| `RETRIEVAL_TOP_K`     | `5`                  | Chunks retrieved per query           |
| `CHUNK_SIZE`          | `500`                | Characters per chunk                 |
| `CHUNK_OVERLAP`       | `50`                 | Overlap between consecutive chunks  |
| `QUERY_EXPANSION`     | `false`              | Generate semantic query variants     |
| `LLM_TEMPERATURE`     | `0.2`                | Generation temperature               |
| `LLM_NUM_CTX`         | `2048`               | Context window (tokens)              |
| `LLM_TOP_P`           | `0.9`                | Nucleus sampling                     |
| `LLM_REPEAT_PENALTY`  | `1.1`                | Repetition penalty                   |

---

## API endpoints

| Method | Path                   | Description                          |
|--------|------------------------|--------------------------------------|
| `POST` | `/documents`           | Ingest a PDF (returns chunk count)   |
| `GET`  | `/documents`           | List all ingested documents          |
| `DELETE`| `/documents/{sha256}` | Delete a document and its chunks     |
| `POST` | `/chat`                | Ask a question (SSE streaming)       |
| `GET`  | `/metrics`             | Aggregate stats for last 10 queries  |

Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Running tests

ChromaDB (`localhost:8001`) and Ollama (`localhost:11435`) must be running.

```bash
# All tests
pytest

# Only repository unit tests (fast, no LLM calls for MetricsStore tests)
pytest tests/test_repositories.py -v

# Only integration tests
pytest tests/test_api.py -v

# Single test
pytest tests/test_api.py::test_upload_document -v
```

---

## Design principles

The codebase follows **SOLID** principles:

- **SRP** — each module has one job (routing, embedding, generation, storage, metrics).
- **OCP** — swap any backend by changing only `main.py` (the composition root).
- **LSP** — concrete classes satisfy their protocols; tests can inject fakes.
- **ISP** — narrow protocols (`Embedder`, `Generator`, `VectorStore`) expose only what callers need.
- **DIP** — `RAGService` and routers depend on abstractions, not concrete classes.

---

## License

MIT — see [LICENSE](LICENSE).

---

## Credits

Built by **[Dani Alva](https://danialva.com)** · AI-assisted with [Claude](https://claude.ai)
