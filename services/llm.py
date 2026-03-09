"""
LLM Generator service — Interface Segregation Principle (ISP).

Defines a narrow Generator protocol so Ollama can be replaced
(e.g. OpenAI, Anthropic) without modifying RAG logic.
"""

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

import ollama


@runtime_checkable
class Generator(Protocol):
    async def generate(self, system: str, user: str) -> str: ...
    async def stream(self, system: str, user: str) -> AsyncIterator[str]: ...


class OllamaGenerator:
    """Generates text responses using a locally running Ollama chat model."""

    def __init__(
        self,
        host: str,
        model: str,
        temperature: float = 0.2,
        num_ctx: int = 2048,
        top_p: float = 0.9,
        repeat_penalty: float = 1.1,
    ) -> None:
        self._client = ollama.AsyncClient(host=host)
        self._model = model
        self._options = {
            "temperature": temperature,
            "num_ctx": num_ctx,
            "top_p": top_p,
            "repeat_penalty": repeat_penalty,
        }

    async def generate(self, system: str, user: str) -> str:
        """Single-shot generation — used for query expansion."""
        response = await self._client.chat(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            options=self._options,
        )
        return response.message.content

    async def stream(self, system: str, user: str) -> AsyncIterator[str]:
        """Token-by-token streaming — used for the final answer."""
        response = await self._client.chat(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            options=self._options,
            stream=True,
        )
        async for chunk in response:
            token = chunk.message.content
            if token:
                yield token
