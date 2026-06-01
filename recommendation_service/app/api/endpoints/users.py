from fastapi import APIRouter, HTTPException, status
import numpy as np
from app.api import schemas
from app.services import chroma_service, vector_service

router = APIRouter()

# Pesos por tipo de interacción
INTERACTION_WEIGHTS = {
    "view": 0.1,
    "like": 0.5,
    "share": 1.5,
    "register": 3.0
}

@router.post("/users/recalculate-profile", response_model=schemas.RecalculateProfileResponse)
async def recalculate_user_profile(data: schemas.RecalculateProfileRequest):
    """
    Recalcula y actualiza el vector de interés del usuario para posts en Chroma
    a partir de un lote de interacciones. No devuelve el vector, solo confirma.
    """
    # Filtrar solo interacciones relacionadas con posts
    post_interactions = [i for i in data.interactions if i.content_type == 'post']
    if not post_interactions:
        return {"status": "no_changes", "detail": "No post interactions to process."}

    post_ids = [i.content_id for i in post_interactions]

    # Obtener vectores de los posts existentes (map id -> vector)
    vectors_map = chroma_service.get_vectors_map_by_ids(post_ids)
    if not vectors_map:
        raise HTTPException(status_code=404, detail="No se encontraron vectores para los posts proporcionados.")

    weighted_vectors = []
    weights = []
    for interaction in post_interactions:
        vec = vectors_map.get(interaction.content_id)
        if vec is None:
            # Ignorar interacciones cuyo content_id no exista en la DB de embeddings
            continue
        w = INTERACTION_WEIGHTS.get(interaction.action, 0.0)
        if w <= 0:
            continue
        weighted_vectors.append(vec * w)
        weights.append(w)

    if not weighted_vectors:
        return {"status": "no_changes", "detail": "No post vectors found or no valid interaction weights."}

    # Obtener vector actual del usuario en Chroma (post interest)
    current_user_vector = chroma_service.get_user_vector(data.user_id, kind='post')

    # Calcular nuevo vector combinando el actual con las interacciones ponderadas
    new_vector = vector_service.calculate_user_profile_vector_batch(
        current_user_vector,
        weighted_vectors,
        weights
    )

    # Guardar en Chroma (upsert único)
    try:
        chroma_service.upsert_user_vector(data.user_id, new_vector, kind='post')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al upsertar vector de usuario: {e}")

    return {"status": "ok", "detail": "User post-interest vector updated."}



@router.post("/users/create", status_code=status.HTTP_201_CREATED)
async def create_user_vectors(payload: schemas.UserCreateRequest):
    """
    [SÍNCRONO] Inicializa al usuario en la colección 'chroma_users' con vectores a cero.
    Se llama directamente desde Django en el proceso de registro de la cuenta.
    """
    try:
        chroma_service.initialize_user(profile_id=payload.profile_id)
        return {"status": "success", "message": f"Usuario {payload.profile_id} inicializado en Chroma."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al inicializar usuario: {str(e)}")