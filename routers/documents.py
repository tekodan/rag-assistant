"""
Documents router — Single Responsibility Principle (SRP).

Handles only the HTTP layer for document ingestion.
Business logic (chunking, embedding, storage) is delegated to services.
"""

import hashlib

import fitz
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from core.config import settings
from models.documents import DeleteResponse, DocumentItem, DocumentResponse
from services.embedder import Embedder
from services.vector_store import VectorStore

router = APIRouter(prefix="/documents", tags=["Documents"])


# ── dependency providers ───────────────────────────────────────────────────────

def get_embedder(request: Request) -> Embedder:
    return request.app.state.embedder


def get_vector_store(request: Request) -> VectorStore:
    return request.app.state.vector_store


# ── helpers ────────────────────────────────────────────────────────────────────

def _chunk_text(text: str) -> list[str]:
    """Split text into overlapping chunks of fixed character size."""
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start : start + settings.chunk_size])
        start += settings.chunk_size - settings.chunk_overlap
    return chunks


# ── endpoint ───────────────────────────────────────────────────────────────────

@router.post("", status_code=201, response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    embedder: Embedder = Depends(get_embedder),
    vector_store: VectorStore = Depends(get_vector_store),
) -> DocumentResponse:
    """
    Ingest a PDF into the vector store.

    - **400** if the file is not a PDF.
    - **409** if an identical document (same SHA-256) was already ingested.
    - **201** with chunk count and document fingerprint on success.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    data = await file.read()
    file_hash = hashlib.sha256(data).hexdigest()

    if vector_store.exists(where={"sha256": file_hash}):
        raise HTTPException(status_code=409, detail="Document already exists")

    pdf = fitz.open(stream=data, filetype="pdf")
    chunks_added = 0

    for page_num, page in enumerate(pdf, start=1):
        page_text = page.get_text()
        if not page_text.strip():
            continue

        for chunk_index, chunk in enumerate(_chunk_text(page_text)):
            chunk_id = f"{file_hash}_p{page_num}_c{chunk_index}"
            embedding = await embedder.embed(chunk)
            vector_store.add(
                chunk_id=chunk_id,
                document=chunk,
                embedding=embedding,
                metadata={"archivo": file.filename, "pagina": page_num, "sha256": file_hash},
            )
            chunks_added += 1

    n_pages = len(pdf)
    pdf.close()

    return DocumentResponse(
        archivo=file.filename,
        sha256=file_hash,
        paginas=n_pages,
        chunks=chunks_added,
    )


@router.get("", response_model=list[DocumentItem])
def list_documents(
    vector_store: VectorStore = Depends(get_vector_store),
) -> list[DocumentItem]:
    """List all ingested documents with their chunk count."""
    return [
        DocumentItem(archivo=d.archivo, sha256=d.sha256, chunks=d.chunks)
        for d in vector_store.list_documents()
    ]


@router.delete("/{sha256}", response_model=DeleteResponse)
def delete_document(
    sha256: str,
    vector_store: VectorStore = Depends(get_vector_store),
) -> DeleteResponse:
    """
    Delete a document and all its chunks from the vector store.

    - **404** if the document does not exist.
    """
    if not vector_store.exists(where={"sha256": sha256}):
        raise HTTPException(status_code=404, detail="Document not found")
    deleted = vector_store.delete_document(sha256)
    return DeleteResponse(sha256=sha256, chunks_deleted=deleted)
