"""
Metrics router — Single Responsibility Principle (SRP).

Exposes aggregate statistics for the last N queries. Read-only endpoint;
all writes happen in the chat router after each query.
"""

from fastapi import APIRouter, Depends, Request

from repositories.metrics import MetricsStore

router = APIRouter(prefix="/metrics", tags=["Metrics"])


def get_metrics_store(request: Request) -> MetricsStore:
    return request.app.state.metrics_store


@router.get("")
def get_metrics(metrics_store: MetricsStore = Depends(get_metrics_store)) -> dict:
    """
    Return aggregate statistics for the last 10 queries.

    - **consultas_registradas**: number of queries in the window.
    - **promedio_tiempo_segundos**: mean response time.
    - **promedio_chunks_encontrados**: mean chunks retrieved before filtering.
    - **tasa_rechazo**: fraction of queries with no relevant context (0–1).
    - **historial**: per-query breakdown, most recent last.
    """
    return metrics_store.summary()
