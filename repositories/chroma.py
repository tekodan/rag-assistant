"""
ChromaVectorStore repository — Dependency Inversion Principle (DIP).

Concrete implementation of the VectorStore protocol backed by ChromaDB.
Swap this file (e.g. for QdrantVectorStore) without touching any service
or router code.
"""

import logging

import chromadb

from services.vector_store import DocumentSummary, SearchResult


class ChromaVectorStore:
    """Persists and retrieves document chunk embeddings in a ChromaDB collection."""

    def __init__(
        self,
        host: str,
        port: int,
        collection_name: str = "documents",
        distance: str = "cosine",
    ) -> None:
        client = chromadb.HttpClient(host=host, port=port)
        self._collection = self._get_or_create(client, collection_name, distance)

    @staticmethod
    def _get_or_create(
        client: chromadb.HttpClient,
        name: str,
        distance: str,
    ) -> chromadb.Collection:
        """
        Return the named collection.  If it exists with a different distance
        metric, delete and recreate it (stale embeddings would be invalid anyway).
        """
        try:
            col = client.get_collection(name)
            current = col.metadata.get("hnsw:space", "l2")
            if current != distance:
                logging.warning(
                    "Collection '%s' uses distance '%s' but '%s' was requested. "
                    "Recreating — existing embeddings will be lost.",
                    name, current, distance,
                )
                client.delete_collection(name)
                return client.create_collection(name, metadata={"hnsw:space": distance})
            return col
        except Exception:
            return client.create_collection(name, metadata={"hnsw:space": distance})

    # ── VectorStore protocol ────────────────────────────────────────────────────

    def add(
        self,
        chunk_id: str,
        document: str,
        embedding: list[float],
        metadata: dict,
    ) -> None:
        self._collection.add(
            ids=[chunk_id],
            documents=[document],
            embeddings=[embedding],
            metadatas=[metadata],
        )

    def exists(self, where: dict) -> bool:
        result = self._collection.get(where=where, limit=1)
        return bool(result["ids"])

    def query(self, embedding: list[float], n_results: int) -> list[SearchResult]:
        result = self._collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        return [
            SearchResult(
                chunk_id=chunk_id,
                document=result["documents"][0][i],
                metadata=result["metadatas"][0][i],
                distance=result["distances"][0][i],
            )
            for i, chunk_id in enumerate(result["ids"][0])
        ]

    def list_documents(self) -> list[DocumentSummary]:
        """Return one summary entry per unique document (grouped by sha256)."""
        result = self._collection.get(include=["metadatas"])
        grouped: dict[str, DocumentSummary] = {}
        for meta in result["metadatas"]:
            sha = meta["sha256"]
            if sha not in grouped:
                grouped[sha] = DocumentSummary(archivo=meta["archivo"], sha256=sha, chunks=0)
            grouped[sha].chunks += 1
        return list(grouped.values())

    def delete_document(self, sha256: str) -> int:
        """Delete all chunks belonging to a document. Returns number of chunks removed."""
        ids = self._collection.get(where={"sha256": sha256})["ids"]
        if ids:
            self._collection.delete(ids=ids)
        return len(ids)
