from pydantic import BaseModel, Field
from typing import List, Optional, Dict

# --- Esquemas para Indexación ---

class IndexPostRequest(BaseModel):
    """Payload para indexar un nuevo post."""
    post_id: str
    tags: Optional[str] = Field(None, description="Una cadena de tags separados por comas.")
    text_content: Optional[str] = None
    image_urls: Optional[List[str]] = Field(None, description="Lista de URLs de imágenes del post.")

class IndexResponse(BaseModel):
    """Respuesta genérica para operaciones de indexación."""
    id: str
    status: str

# --- Esquemas para Perfil de Usuario ---

class InteractionItem(BaseModel):
    content_id: str
    content_type: str
    action: str


class RecalculateProfileRequest(BaseModel):
    """Payload para recalcular el vector de intereses de un usuario en lote."""
    user_id: str
    interactions: List[InteractionItem]


class RecalculateProfileResponse(BaseModel):
    """Respuesta de confirmación tras recalcular el vector (no devuelve el vector)."""
    status: str
    detail: Optional[str] = None

# --- Esquemas para Recomendaciones ---

class RecommendedPostItem(BaseModel):
    """Un post recomendado con su ID y score de similitud."""
    post_id: str
    score: float

class RecommendationRequest(BaseModel):
    """Payload para solicitar recomendaciones."""
    profile_id: Optional[str] = Field(None, description="ID del perfil del usuario para obtener su vector de interés desde Chroma.")
    user_vector: Optional[List[float]] = Field(None, description="Vector de interés del usuario, usado cuando no se pasa profile_id.")
    exclude_ids: Optional[List[str]] = Field(default_factory=list, description="Lista de IDs de post a excluir (ej. ya vistos).")
    limit: int = Field(10, gt=0, le=1000)

class RecommendationResponse(BaseModel):
    """Respuesta con la lista de posts recomendados y sus scores."""
    recommended_posts: List[RecommendedPostItem]

# 1. Schema para la creación síncrona
class UserCreateRequest(BaseModel):
    profile_id: str