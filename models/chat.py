from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Pregunta del usuario")
    n_results: int = Field(default=5, ge=1, le=20, description="Máximo de chunks a recuperar")


class QueryMetrics(BaseModel):
    tiempo_respuesta: float = Field(description="Segundos totales de la consulta")
    chunks_encontrados: int = Field(description="Chunks recuperados de ChromaDB antes del filtro")
    chunks_usados: int = Field(description="Chunks que superaron el umbral de similitud")
    distancia_promedio: float | None = Field(description="Distancia coseno promedio de los chunks usados")
    modelo_usado: str = Field(description="Modelo LLM que generó la respuesta")


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict]
    metrics: QueryMetrics
