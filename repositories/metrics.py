"""
MetricsRepository — Single Responsibility Principle (SRP).

Stores query records in a bounded in-memory deque and computes aggregate
statistics.  Completely decoupled from RAG logic and the HTTP layer.
"""

from collections import deque
from dataclasses import dataclass


@dataclass
class QueryRecord:
    tiempo_respuesta: float
    chunks_encontrados: int
    chunks_usados: int
    distancia_promedio: float | None
    modelo_usado: str
    rechazada: bool


class MetricsStore:
    """Thread-safe in-memory store for the last N query records."""

    def __init__(self, max_history: int = 10) -> None:
        self._history: deque[QueryRecord] = deque(maxlen=max_history)

    def record(self, entry: QueryRecord) -> None:
        self._history.append(entry)

    def summary(self) -> dict:
        records = list(self._history)
        n = len(records)

        if not records:
            return {
                "consultas_registradas": 0,
                "promedio_tiempo_segundos": None,
                "promedio_chunks_encontrados": None,
                "tasa_rechazo": None,
                "historial": [],
            }

        avg_tiempo  = round(sum(r.tiempo_respuesta    for r in records) / n, 3)
        avg_chunks  = round(sum(r.chunks_encontrados  for r in records) / n, 1)
        tasa_rechazo = round(sum(1 for r in records if r.rechazada) / n, 3)

        return {
            "consultas_registradas": n,
            "promedio_tiempo_segundos": avg_tiempo,
            "promedio_chunks_encontrados": avg_chunks,
            "tasa_rechazo": tasa_rechazo,
            "historial": [
                {
                    "tiempo_respuesta":    r.tiempo_respuesta,
                    "chunks_encontrados":  r.chunks_encontrados,
                    "chunks_usados":       r.chunks_usados,
                    "distancia_promedio":  r.distancia_promedio,
                    "modelo_usado":        r.modelo_usado,
                    "rechazada":           r.rechazada,
                }
                for r in records
            ],
        }
