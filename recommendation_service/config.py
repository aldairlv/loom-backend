import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Configuración de la aplicación cargada desde variables de entorno.
    """
    PROJECT_NAME: str = "Loom Recommendation Service"

    # Configuración de ChromaDB
    CHROMA_HOST: str = os.getenv("CHROMA_HOST", "localhost")
    CHROMA_PORT: int = int(os.getenv("CHROMA_PORT", "8000"))

    # Configuración del modelo de embedding
    # Usamos un modelo multimodal (texto e imagen) de CLIP.
    EMBEDDING_MODEL_NAME: str = 'clip-ViT-B-32'

    class Config:
        case_sensitive = True

settings = Settings()