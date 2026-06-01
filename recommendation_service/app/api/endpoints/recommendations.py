from fastapi import APIRouter
import numpy as np
from app.api import schemas
from app.services import chroma_service

router = APIRouter()

@router.post("/recommendations/posts", response_model=schemas.RecommendationResponse)
async def get_post_recommendations(data: schemas.RecommendationRequest):
    """
    Recibe el profile_id de un usuario, recupera su vector de interés,
    y devuelve una lista de hasta 'limit' IDs de posts similares, 
    excluyendo los que ya ha visto.
    """
    # 1. Obtener el vector del usuario desde Chroma (o tu servicio de perfiles)
    # Asumimos que chroma_service tiene un método para recuperar el embedding del usuario
    if data.user_vector is not None:
        user_vector = np.array(data.user_vector)
    elif data.profile_id is not None:
        user_vector = chroma_service.get_user_vector(data.profile_id, kind='post')
    else:
        return {"recommended_posts": []}

    if user_vector is None or len(user_vector) == 0:
        return {"recommended_posts": []}
    
    # 2. Buscar los posts más cercanos usando el vector del usuario
    # Le pasamos data.exclude_ids para que ChromaDB no calcule similitud sobre lo ya visto
    recommended_posts = chroma_service.query_similar_posts(
        vector=np.array(user_vector),
        limit=data.limit,
        exclude_ids=data.exclude_ids or []
    )
    
    return {"recommended_posts": recommended_posts}