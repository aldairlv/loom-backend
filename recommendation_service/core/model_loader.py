from sentence_transformers import SentenceTransformer

# --- Configuración del Modelo ---
# Usamos un modelo ligero y eficiente, ideal para empezar.
MODEL_NAME = 'clip-ViT-B-32'#'all-MiniLM-L6-v2'

# --- Singleton para el Modelo ---
# Esta variable global almacenará el modelo una vez cargado para no volver a cargarlo.
_model = None

def get_model():
    """
    Carga y devuelve el modelo SentenceTransformer.

    Utiliza un patrón singleton para asegurar que el modelo solo se cargue en memoria una vez,
    mejorando el rendimiento y el uso de memoria.
    """
    global _model
    if _model is None:
        print(f"🚀 Cargando el modelo de embedding '{MODEL_NAME}' en memoria...")
        _model = SentenceTransformer(MODEL_NAME)
        print("✅ Modelo cargado exitosamente.")
    return _model