from fastapi import APIRouter, HTTPException
import numpy as np
from app.api import schemas
from app.services import embedder, chroma_service

router = APIRouter()

@router.post("/index/post", response_model=schemas.IndexResponse)
async def index_post(data: schemas.IndexPostRequest):
    """
    Recibe los datos de un post, genera su embedding y lo indexa en ChromaDB.
    Si el post tiene texto e imagen, crea un embedding multimodal promediando ambos vectores.
    """
    vectors_to_average = []
    
    # 1. Generar embedding de texto si existe
    if data.text_content or data.tags:
        tags_str = f"Tags: {data.tags}." if data.tags else ""
        content_str = f"Contenido: {data.text_content}" if data.text_content else ""
        full_text = " ".join(filter(None, [tags_str, content_str]))
        text_vector = embedder.get_text_embedding(full_text)
        vectors_to_average.append(text_vector)

    # 2. Generar embedding de imagen si existe
    if data.image_urls:
        for image_url in data.image_urls:
            try:
                image_vector = embedder.get_image_embedding(image_url)
                vectors_to_average.append(image_vector)
            except Exception as e:
                print(f"WARN: No se pudo procesar la imagen {image_url} para el post {data.post_id}: {e}")

    if not vectors_to_average:
        raise HTTPException(status_code=400, detail="El post debe tener al menos texto o una URL de imagen para ser indexado.")

    # 3. Calcular el vector final (promedio) y guardarlo
    final_vector = np.mean(vectors_to_average, axis=0)
    metadata = {"tags": data.tags or "", "has_image": bool(data.image_urls)}
    
    try:
        chroma_service.save_post_vector(data.post_id, final_vector, metadata)
    except Exception as e:
        error_msg = str(e)
        print(f"ERROR al indexar post {data.post_id}: {error_msg}")
        # Si es un error de colección no encontrada, dar más contexto
        if "does not exist" in error_msg or "NotFound" in error_msg:
            raise HTTPException(
                status_code=503,
                detail="ChromaDB no está disponible o las colecciones no están inicializadas. Reintenta en unos segundos."
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Error al indexar el post: {error_msg}"
            )

    return {"id": data.post_id, "status": "indexed"}