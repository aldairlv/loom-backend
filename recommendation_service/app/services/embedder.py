from sentence_transformers import SentenceTransformer
from PIL import Image
import requests
from io import BytesIO
import numpy as np
import logging
from config import settings

logger = logging.getLogger(__name__)

# --- Singleton para el Modelo ---
# Esta variable global almacenará el modelo una vez cargado para no volver a cargarlo.
_model = None

def load_model():
    """
    Carga el modelo SentenceTransformer en la variable global _model.
    Utiliza un patrón singleton para asegurar que el modelo solo se cargue en memoria una vez.
    Esta función es llamada por el 'lifespan' de FastAPI al iniciar la app.
    """
    global _model
    if _model is None:
        print(f"INFO:     Cargando el modelo de embedding '{settings.EMBEDDING_MODEL_NAME}' en memoria...")
        _model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
        print("INFO:     ✅ Modelo cargado exitosamente.")

def get_text_embedding(text: str) -> np.ndarray:
    """Genera un vector de embedding para un texto dado."""
    if _model is None:
        raise RuntimeError("El modelo no ha sido cargado. Llama a 'load_model()' primero.")
    # El modelo puede truncar textos largos, pero es bueno controlarlo.
    # Un límite de 512 caracteres suele ser seguro para modelos de transformers.
    truncated_text = text[:512]
    return _model.encode(truncated_text, convert_to_numpy=True)

def get_image_embedding(image_url: str) -> np.ndarray:
    """
    Descarga una imagen desde una URL y genera su vector de embedding.
    """
    if _model is None:
        raise RuntimeError("El modelo no ha sido cargado. Llama a 'load_model()' primero.")
    
    try:
        response = requests.get(image_url, stream=True, timeout=10)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content))
        return _model.encode(image, convert_to_numpy=True)
    except requests.RequestException as e:
        print(f"ERROR:    Error al descargar la imagen desde {image_url}: {e}")
        raise
    except Exception as e:
        print(f"ERROR:    Error al procesar la imagen desde {image_url}: {e}")
        raise