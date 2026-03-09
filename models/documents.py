from pydantic import BaseModel


class DocumentResponse(BaseModel):
    archivo: str
    sha256: str
    paginas: int
    chunks: int


class DocumentItem(BaseModel):
    archivo: str
    sha256: str
    chunks: int


class DeleteResponse(BaseModel):
    sha256: str
    chunks_deleted: int
