"""
Test configuration for integration tests.

Uses FastAPI's TestClient (in-process) with a dedicated 'test_documents'
ChromaDB collection so tests NEVER touch the production 'documents' collection.

Services required (must be running before pytest):
  - ChromaDB on localhost:8001
  - Ollama   on localhost:11435
"""

import hashlib
import io
import os

# ── env vars must be set BEFORE importing any app module ──────────────────────
os.environ["CHROMA_HOST"] = "localhost"
os.environ["CHROMA_PORT"] = "8001"
os.environ["CHROMA_COLLECTION"] = "test_documents"   # isolated collection
os.environ["CHROMA_DISTANCE"] = "cosine"
os.environ["OLLAMA_HOST"] = "http://localhost:11435"
os.environ["EMBED_MODEL"] = "nomic-embed-text"
os.environ["CHAT_MODEL"] = "llama3.2:1b"
os.environ["SIMILARITY_THRESHOLD"] = "0.5"
os.environ["RETRIEVAL_TOP_K"] = "5"
os.environ["LLM_TEMPERATURE"] = "0.2"
os.environ["LLM_NUM_CTX"] = "4096"
os.environ["LLM_TOP_P"] = "0.9"
os.environ["LLM_REPEAT_PENALTY"] = "1.1"

import fitz                          # noqa: E402
import pytest                        # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from main import app                 # noqa: E402  (config already resolved above)
from repositories.chroma import ChromaVectorStore   # noqa: E402
from repositories.metrics import MetricsStore       # noqa: E402


# ── repository fixtures ────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def chroma_repo() -> ChromaVectorStore:
    """Direct access to the test ChromaDB repository (same isolated collection)."""
    return ChromaVectorStore(
        host="localhost",
        port=8001,
        collection_name="test_documents",
        distance="cosine",
    )


@pytest.fixture(scope="session")
def metrics_repo() -> MetricsStore:
    """Isolated in-memory MetricsStore for unit-level repository tests."""
    return MetricsStore(max_history=10)


# ── client fixture ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def client() -> TestClient:
    """
    In-process TestClient backed by the 'test_documents' collection.
    The collection is wiped at session teardown.
    """
    with TestClient(app) as c:
        yield c
        # Teardown: remove all test documents
        docs = c.get("/documents").json()
        for doc in docs:
            c.delete(f"/documents/{doc['sha256']}")


# ── PDF fixture ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def test_pdf() -> bytes:
    """Generate an in-memory PDF with known content about database migrations."""
    doc = fitz.open()
    page = doc.new_page()
    content = (
        "Database Migrations Guide\n\n"
        "Chapter 1: What is a migration?\n\n"
        "A database migration is a controlled, versioned change to a database schema. "
        "Migrations allow teams to evolve the database structure over time without "
        "losing existing data. Each migration describes a transformation: adding a column, "
        "renaming a table, creating an index, or modifying constraints.\n\n"
        "Chapter 2: Why use migrations?\n\n"
        "Migrations solve the problem of keeping database schemas in sync across "
        "development, staging, and production environments. Without migrations, "
        "schema changes are applied manually and are error-prone. With migrations, "
        "every change is tracked in version control alongside the application code.\n\n"
        "Chapter 3: Types of migrations\n\n"
        "1. Schema migrations: structural changes (CREATE TABLE, ALTER COLUMN).\n"
        "2. Data migrations: transforming existing rows (backfilling, normalizing).\n"
        "3. Rollback migrations: reverting a previous change if something goes wrong.\n"
    )
    page.insert_text((50, 50), content, fontsize=11)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


@pytest.fixture(scope="session")
def uploaded_pdf(client: TestClient, test_pdf: bytes) -> dict:
    """
    Upload the test PDF once per session. Returns the response body.
    Accepts 201 (new) or 409 (already exists from a previous run).
    """
    response = client.post(
        "/documents",
        files={"file": ("migrations_guide.pdf", test_pdf, "application/pdf")},
    )

    if response.status_code == 201:
        return response.json()

    if response.status_code == 409:
        sha256 = hashlib.sha256(test_pdf).hexdigest()
        return {"archivo": "migrations_guide.pdf", "sha256": sha256, "chunks": -1}

    pytest.fail(f"Unexpected upload status: {response.status_code} {response.text}")
