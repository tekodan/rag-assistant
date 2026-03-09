# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Start all services
docker compose up --build

# Run FastAPI locally (without Docker)
uvicorn main:app --reload

# Run tests
pytest

# Run a single test
pytest tests/test_foo.py::test_bar
```

## Architecture

Three-service RAG stack orchestrated via Docker Compose:

- **api** (FastAPI, port 8000) — handles document ingestion and chat endpoints. Entry point is `main.py`.
- **chromadb** (port 8001 on host, 8000 internally) — vector store. Connect via `CHROMA_HOST` / `CHROMA_PORT` env vars.
- **ollama** (port 11434) — local LLM inference. Connect via `OLLAMA_HOST` env var (`http://ollama:11434` inside Docker).

### Environment variables (set by docker-compose)

| Variable | Default | Purpose |
|---|---|---|
| `CHROMA_HOST` | `chromadb` | ChromaDB service hostname |
| `CHROMA_PORT` | `8001` | ChromaDB service port |
| `OLLAMA_HOST` | `http://ollama:11434` | Ollama base URL |

### Data flow

`POST /documents` → parse PDF (PyMuPDF) → embed (Ollama) → store in ChromaDB
`POST /chat` → embed query (Ollama) → similarity search in ChromaDB → generate response (Ollama)
