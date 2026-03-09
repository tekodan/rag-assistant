"""
Integration tests for the RAG API.

Uses FastAPI's TestClient (in-process) with an isolated 'test_documents'
ChromaDB collection. Production data is never touched.

Prerequisites (must be running): ChromaDB on localhost:8001, Ollama on localhost:11435
Run all:    pytest tests/
Run single: pytest tests/test_api.py::test_upload_document -v
"""

import pytest
from fastapi.testclient import TestClient


# ── Document ingestion ─────────────────────────────────────────────────────────

def test_upload_document(client: TestClient, test_pdf: bytes):
    """Uploading a valid PDF returns 201 with chunk count and SHA-256."""
    response = client.post(
        "/documents",
        files={"file": ("migrations_guide.pdf", test_pdf, "application/pdf")},
    )

    # May already exist from a previous run — both are acceptable here
    assert response.status_code in (201, 409)

    if response.status_code == 201:
        data = response.json()
        assert data["archivo"] == "migrations_guide.pdf"
        assert isinstance(data["sha256"], str) and len(data["sha256"]) == 64
        assert data["chunks"] > 0
        assert data["paginas"] >= 1


def test_duplicate_document(client: TestClient, uploaded_pdf: dict, test_pdf: bytes):
    """Uploading the same PDF a second time returns 409 Conflict."""
    response = client.post(
        "/documents",
        files={"file": ("migrations_guide.pdf", test_pdf, "application/pdf")},
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


def test_upload_rejects_non_pdf(client: TestClient):
    """Uploading a non-PDF file returns 400."""
    response = client.post(
        "/documents",
        files={"file": ("data.txt", b"hello world", "text/plain")},
    )
    assert response.status_code == 400


# ── Chat ───────────────────────────────────────────────────────────────────────

def test_chat_with_context(client: TestClient, uploaded_pdf: dict):
    """
    A question related to the uploaded PDF should return an answer with sources.
    The `uploaded_pdf` fixture ensures the document is ingested before this runs.
    """
    response = client.post("/chat", json={"query": "What is a database migration?"})

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data["answer"], str) and len(data["answer"]) > 0

    # Must include at least one source citation
    assert len(data["sources"]) > 0, "Expected citations but got none"
    assert "archivo" in data["sources"][0]
    assert "pagina" in data["sources"][0]

    # Metrics sanity checks
    m = data["metrics"]
    assert m["chunks_usados"] > 0
    assert m["tiempo_respuesta"] > 0
    assert m["modelo_usado"] != ""


def test_chat_empty_query_rejected(client: TestClient):
    """An empty query string should be rejected by validation (422)."""
    response = client.post("/chat", json={"query": ""})
    assert response.status_code == 422


# ── Documents CRUD ─────────────────────────────────────────────────────────────

def test_list_documents(client: TestClient, uploaded_pdf: dict):
    """GET /documents returns a list that includes the uploaded document."""
    response = client.get("/documents")

    assert response.status_code == 200
    docs = response.json()
    assert isinstance(docs, list) and len(docs) > 0

    sha256s = [d["sha256"] for d in docs]
    assert uploaded_pdf["sha256"] in sha256s


# ── Metrics ────────────────────────────────────────────────────────────────────

def test_metrics_after_chat(client: TestClient, uploaded_pdf: dict):
    """GET /metrics reflects at least one recorded query."""
    client.post("/chat", json={"query": "Explain schema migrations briefly."})

    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()

    assert data["consultas_registradas"] >= 1
    assert data["promedio_tiempo_segundos"] is not None
    assert isinstance(data["historial"], list) and len(data["historial"]) >= 1

    entry = data["historial"][0]
    assert "tiempo_respuesta" in entry
    assert "chunks_encontrados" in entry
    assert "rechazada" in entry


# ── Rejection ─────────────────────────────────────────────────────────────────

def test_chat_rejection(client: TestClient):
    """
    Verify the rejection pathway against an empty collection.

    The test_documents collection starts empty (no uploaded_pdf fixture here),
    so any query must be rejected. No production data is touched.
    """
    response = client.post("/chat", json={"query": "Qué es una migración?"})
    assert response.status_code == 200
    data = response.json()

    assert data["sources"] == [], "Empty collection must return no sources"
    assert data["metrics"]["chunks_usados"] == 0
    assert "No encontré" in data["answer"]
