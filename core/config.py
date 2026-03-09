import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    chroma_host: str
    chroma_port: int
    chroma_distance: str       # cosine | l2 | ip
    chroma_collection: str     # ChromaDB collection name
    ollama_host: str
    embed_model: str
    chat_model: str
    chunk_size: int
    chunk_overlap: int
    similarity_threshold: float
    retrieval_top_k: int
    # Ollama generation parameters
    query_expansion: bool      # disable on CPU — saves 3 extra Ollama calls
    llm_temperature: float     # 0.0 = deterministic, 1.0 = very creative
    llm_num_ctx: int           # context window in tokens (chunks + answer)
    llm_top_p: float           # nucleus sampling — 0.9 is a good balance
    llm_repeat_penalty: float  # penalises repetition — values >1 reduce it


settings = Settings(
    chroma_host=os.getenv("CHROMA_HOST", "chromadb"),
    chroma_port=int(os.getenv("CHROMA_PORT", "8000")),
    chroma_distance=os.getenv("CHROMA_DISTANCE", "cosine"),
    chroma_collection=os.getenv("CHROMA_COLLECTION", "documents"),
    ollama_host=os.getenv("OLLAMA_HOST", "http://ollama:11434"),
    embed_model=os.getenv("EMBED_MODEL", "nomic-embed-text"),
    chat_model=os.getenv("CHAT_MODEL", "llama3.2:1b"),
    chunk_size=int(os.getenv("CHUNK_SIZE", "500")),
    chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "50")),
    similarity_threshold=float(os.getenv("SIMILARITY_THRESHOLD", "0.8")),
    retrieval_top_k=int(os.getenv("RETRIEVAL_TOP_K", "5")),
    query_expansion=os.getenv("QUERY_EXPANSION", "false").lower() == "true",
    llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.2")),
    llm_num_ctx=int(os.getenv("LLM_NUM_CTX", "4096")),
    llm_top_p=float(os.getenv("LLM_TOP_P", "0.9")),
    llm_repeat_penalty=float(os.getenv("LLM_REPEAT_PENALTY", "1.1")),
)
