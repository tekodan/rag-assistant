"""
Embedder service — Interface Segregation Principle (ISP).

Defines a narrow Embedder protocol so any implementation (Ollama, OpenAI, etc.)
can be swapped without touching calling code.
"""

from typing import Protocol, runtime_checkable

import ollama


@runtime_checkable
class Embedder(Protocol):
    async def embed(self, text: str) -> list[float]: ...


class OllamaEmbedder:
    """Generates text embeddings using a locally running Ollama model."""

    def __init__(self, host: str, model: str) -> None:
        self._client = ollama.AsyncClient(host=host)
        self._model = model

    async def embed(self, text: str) -> list[float]:
        response = await self._client.embeddings(model=self._model, prompt=text)
        return response.embedding
