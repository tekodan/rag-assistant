"""
VectorStore protocol — Interface Segregation Principle (ISP).

Defines a narrow interface so any backend (ChromaDB, Qdrant, Pinecone…)
can be injected without modifying RAG or router logic.
Concrete implementations live in repositories/.
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class SearchResult:
    chunk_id: str
    document: str
    metadata: dict
    distance: float


@dataclass
class DocumentSummary:
    archivo: str
    sha256: str
    chunks: int


@runtime_checkable
class VectorStore(Protocol):
    def add(
        self,
        chunk_id: str,
        document: str,
        embedding: list[float],
        metadata: dict,
    ) -> None: ...

    def exists(self, where: dict) -> bool: ...

    def query(self, embedding: list[float], n_results: int) -> list[SearchResult]: ...

    def list_documents(self) -> list[DocumentSummary]: ...

    def delete_document(self, sha256: str) -> int: ...
