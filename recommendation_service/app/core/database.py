"""import chromadb
import time
from config import settings

# --- Cliente de ChromaDB ---
# Se crea una única instancia del cliente para ser reutilizada en toda la aplicación.
def _initialize_chroma_client(max_retries=5, retry_delay=2):
    
    # Intenta conectar con ChromaDB con reintentos exponenciales.
    
    for attempt in range(max_retries):
        try:
            client = chromadb.HttpClient(
                host=settings.CHROMA_HOST,
                port=settings.CHROMA_PORT
            )
            # Verificar que el cliente está realmente conectado
            client.heartbeat()
            print(f"✓ ChromaDB cliente conectado exitosamente en intento {attempt + 1}")
            return client
        except Exception as e:
            print(f"⚠ Intento {attempt + 1}/{max_retries} falló: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                raise RuntimeError(
                    f"No se pudo conectar a ChromaDB después de {max_retries} intentos. "
                    f"Host: {settings.CHROMA_HOST}:{settings.CHROMA_PORT}"
                )

client = _initialize_chroma_client()

# --- Colecciones ---
# Obtenemos o creamos las colecciones necesarias. Cada colección almacena un tipo
# de embedding (posts, usuarios, etc.).
# El `embedding_function` se define como None porque generaremos los vectores
# manualmente con nuestro modelo CLIP antes de insertarlos.

def _initialize_posts_collection(max_retries=3):
    
    # Obtiene o crea la colección de posts con manejo de reintentos.
    
    for attempt in range(max_retries):
        try:
            collection = client.get_or_create_collection(
                name="posts_v4",
                metadata={"hnsw:space": "cosine"}
            )
            print(f"✓ Colección 'posts_v4' inicializada correctamente")
            return collection
        except Exception as e:
            print(f"⚠ Intento {attempt + 1}/{max_retries} para crear colección falló: {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                raise RuntimeError(
                    f"No se pudo crear/obtener la colección 'posts_v4' después de {max_retries} intentos"
                )

posts_collection = _initialize_posts_collection()
# Podrías añadir más colecciones aquí en el futuro, por ejemplo:
# events_collection = client.get_or_create_collection(name="events_v1")"""


import chromadb
import time
from config import settings

def _initialize_chroma_client(max_retries=5, retry_delay=2):
    for attempt in range(max_retries):
        try:
            client = chromadb.HttpClient(
                host=settings.CHROMA_HOST,
                port=settings.CHROMA_PORT
            )
            client.heartbeat()
            print(f"✓ ChromaDB cliente conectado exitosamente")
            return client
        except Exception as e:
            print(f"⚠ Intento {attempt + 1}/{max_retries} falló: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                raise RuntimeError(f"No se pudo conectar a ChromaDB")

client = _initialize_chroma_client()

# --- Función Auxiliar Genérica de Inicialización ---
def _get_collection_safe(name: str, max_retries=3):
    for attempt in range(max_retries):
        try:
            collection = client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"} # Distancia Coseno para embeddings de CLIP
            )
            print(f"✓ Colección '{name}' inicializada correctamente")
            return collection
        except Exception as e:
            print(f"⚠ Intento {attempt + 1}/{max_retries} para '{name}' falló: {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                raise RuntimeError(f"Error crítico al crear colección '{name}'")

# --- Exportación de Colecciones ---
posts_collection = _get_collection_safe("posts_v4")
events_collection = _get_collection_safe("events_v1")
users_collection = _get_collection_safe("users_v1")