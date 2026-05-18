import os
import chromadb
from chromadb.utils import embedding_functions
from .model_loader import get_model, MODEL_NAME

# 1. Cargar el modelo de embedding una sola vez
sentence_transformer_model = get_model()

# 2. Crear una función de embedding compatible con Chroma
embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=MODEL_NAME
)

# 3. Obtener los detalles de conexión desde las variables de entorno
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = os.getenv("CHROMA_PORT", "8000")

# 4. Crear el cliente de ChromaDB
client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

# 5. Obtener o crear la colección y asignarla a la variable 'collection'
#    Esta es la variable que se importará en otros archivos.
collection = client.get_or_create_collection(
    name="posts_v3", embedding_function=embedding_function
)