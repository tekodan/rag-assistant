"""
Unit tests for repository layer.

These tests exercise ChromaVectorStore and MetricsStore directly,
without going through the HTTP layer.  ChromaDB must be running on
localhost:8001 (same requirement as the integration tests).
"""

import pytest

from repositories.chroma import ChromaVectorStore
from repositories.metrics import MetricsStore, QueryRecord


# ── MetricsStore ───────────────────────────────────────────────────────────────

def test_metrics_empty_summary(metrics_repo: MetricsStore):
    """Fresh store returns zero counts and None averages."""
    data = metrics_repo.summary()
    assert data["consultas_registradas"] == 0
    assert data["promedio_tiempo_segundos"] is None
    assert data["tasa_rechazo"] is None
    assert data["historial"] == []


def test_metrics_record_and_summary(metrics_repo: MetricsStore):
    """Recording a query is reflected in the summary."""
    metrics_repo.record(QueryRecord(
        tiempo_respuesta=1.5,
        chunks_encontrados=5,
        chunks_usados=3,
        distancia_promedio=0.25,
        modelo_usado="llama3.2:1b",
        rechazada=False,
    ))

    data = metrics_repo.summary()
    assert data["consultas_registradas"] >= 1
    assert data["promedio_tiempo_segundos"] is not None
    assert isinstance(data["historial"], list) and len(data["historial"]) >= 1

    entry = data["historial"][-1]
    assert entry["tiempo_respuesta"] == 1.5
    assert entry["chunks_encontrados"] == 5
    assert entry["chunks_usados"] == 3
    assert entry["rechazada"] is False


def test_metrics_rejection_rate(metrics_repo: MetricsStore):
    """Rejection rate is computed correctly."""
    metrics_repo.record(QueryRecord(
        tiempo_respuesta=0.5,
        chunks_encontrados=0,
        chunks_usados=0,
        distancia_promedio=None,
        modelo_usado="llama3.2:1b",
        rechazada=True,
    ))

    data = metrics_repo.summary()
    assert 0.0 < data["tasa_rechazo"] <= 1.0


def test_metrics_bounded_history():
    """Store respects max_history and discards oldest records."""
    store = MetricsStore(max_history=3)
    for i in range(5):
        store.record(QueryRecord(
            tiempo_respuesta=float(i),
            chunks_encontrados=i,
            chunks_usados=i,
            distancia_promedio=None,
            modelo_usado="test",
            rechazada=False,
        ))

    data = store.summary()
    assert data["consultas_registradas"] == 3
    # Oldest two records (tiempo=0,1) must have been evicted
    times = [r["tiempo_respuesta"] for r in data["historial"]]
    assert 0.0 not in times and 1.0 not in times


# ── ChromaVectorStore ──────────────────────────────────────────────────────────

def test_chroma_exists_false_on_unknown(chroma_repo: ChromaVectorStore):
    """exists() returns False for a sha256 that was never added."""
    assert chroma_repo.exists(where={"sha256": "nonexistent_sha"}) is False


def test_chroma_add_exists_delete(chroma_repo: ChromaVectorStore):
    """Round-trip: add a chunk, verify it exists, then delete it."""
    sha = "test_repo_sha_001"
    chunk_id = f"{sha}_p1_c0"
    embedding = [0.1] * 768  # fake embedding — dimension must match nomic-embed-text

    chroma_repo.add(
        chunk_id=chunk_id,
        document="Repository pattern test chunk.",
        embedding=embedding,
        metadata={"archivo": "test.pdf", "pagina": 1, "sha256": sha},
    )

    assert chroma_repo.exists(where={"sha256": sha}) is True

    deleted = chroma_repo.delete_document(sha)
    assert deleted == 1
    assert chroma_repo.exists(where={"sha256": sha}) is False


def test_chroma_list_documents_includes_added(chroma_repo: ChromaVectorStore):
    """list_documents() reflects chunks inserted via the repository."""
    sha = "test_repo_sha_002"
    for i in range(2):
        chroma_repo.add(
            chunk_id=f"{sha}_p1_c{i}",
            document=f"Chunk {i} content.",
            embedding=[0.2] * 768,
            metadata={"archivo": "list_test.pdf", "pagina": 1, "sha256": sha},
        )

    docs = chroma_repo.list_documents()
    found = [d for d in docs if d.sha256 == sha]
    assert len(found) == 1
    assert found[0].chunks == 2

    # Cleanup
    chroma_repo.delete_document(sha)
