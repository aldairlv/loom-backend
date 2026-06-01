from typing import List, Optional
import numpy as np
import logging
from app.core.database import posts_collection, users_collection

logger = logging.getLogger(__name__)

# ==========================================
#          SECCIÓN: POSTS
# ==========================================


def save_post_vector(post_id: str, vector: np.ndarray, metadata: dict):
    """
    Guarda o actualiza el vector de un post en ChromaDB.
    Usa 'upsert' para ser idempotente: si el ID ya existe, lo actualiza; si no, lo crea.
    """
    logger.info(f"[CHROMA] save_post_vector: Guardando vector para post_id={post_id}")
    logger.debug(f"[CHROMA] save_post_vector: Vector shape={vector.shape}, metadata={metadata}")
    
    posts_collection.upsert(
        ids=[str(post_id)],
        embeddings=[vector.tolist()],
        metadatas=[metadata]
    )
    
    logger.info(f"[CHROMA] save_post_vector: ✅ Post {post_id} guardado exitosamente en ChromaDB")

def get_vectors_by_ids(ids: List[str]) -> List[np.ndarray]:
    """
    Recupera los vectores de embedding para una lista de IDs de post.
    """
    if not ids:
        return []
    results = posts_collection.get(ids=ids, include=['embeddings'])
    return [np.array(emb) for emb in results['embeddings']]


def get_vectors_map_by_ids(ids: List[str]) -> dict:
    """
    Recupera un mapeo id -> vector para los IDs proporcionados (posts).
    """
    logger.info(f"[CHROMA] get_vectors_map_by_ids: Buscando vectores para {len(ids)} posts: {ids}")
    
    if not ids:
        logger.warning("[CHROMA] get_vectors_map_by_ids: Lista de IDs vacía")
        return {}
    
    results = posts_collection.get(ids=ids, include=['embeddings'])
    ids_found = results.get('ids', [])
    embeddings = results.get('embeddings', [])
    
    logger.info(f"[CHROMA] get_vectors_map_by_ids: Encontrados {len(ids_found)} posts en ChromaDB (solicitados {len(ids)})")
    logger.debug(f"[CHROMA] get_vectors_map_by_ids: IDs encontrados: {ids_found}")
    
    vectors_map = {id_: np.array(emb) for id_, emb in zip(ids_found, embeddings)}
    logger.info(f"[CHROMA] get_vectors_map_by_ids: Mapa retornado con {len(vectors_map)} vectores")
    
    return vectors_map

def _distance_to_similarity(distance: float) -> float:
    """Convierte una distancia de Chroma en un score de similitud normalizado."""
    try:
        score = 1.0 - float(distance)
    except Exception:
        score = 0.0
    return max(0.0, min(1.0, score))


def query_similar_posts(vector: np.ndarray, limit: int, exclude_ids: List[str] = None) -> List[dict]:
    """
    Busca los posts más similares a un vector dado, excluyendo ciertos IDs.
    Devuelve una lista de objetos con post_id y score.
    """
    fetch_limit = limit + (len(exclude_ids) if exclude_ids else 0) + 10
    
    results = posts_collection.query(
        query_embeddings=[vector.tolist()],
        n_results=fetch_limit,
        include=['distances']
    )

    ids = results.get('ids', [[]])[0] if results.get('ids') else []
    distances = results.get('distances', [[]])[0] if results.get('distances') else []
    
    recommended = []
    for index, post_id in enumerate(ids):
        if exclude_ids and post_id in exclude_ids:
            continue
        score = 0.0
        if index < len(distances):
            score = _distance_to_similarity(distances[index])
        recommended.append({
            'post_id': post_id,
            'score': score,
        })
        if len(recommended) >= limit:
            break

    return recommended


# ==========================================
#          SECCIÓN: USUARIOS (PROFILES)
# ==========================================

def initialize_user(profile_id: str):
    """
    [SÍNCRONO] Registra al usuario con vectores vacíos (ceros) en Chroma.
    Crea dos entradas para separar los intereses de Tumblr y de Meetup.
    """
    # Vector base vacío (Suponiendo 512 dimensiones de tu modelo CLIP)
    zero_vector = np.zeros(512).tolist()
    
    users_collection.upsert(
        ids=[f"{profile_id}_post", f"{profile_id}_event"],
        embeddings=[zero_vector, zero_vector],
        metadatas=[{"type": "post_interest"}, {"type": "event_interest"}]
    )


def get_user_vector(profile_id: str, kind: str = 'post') -> Optional[np.ndarray]:
    """
    Recupera el vector de interés del usuario para 'post' o 'event'.
    Devuelve None si no existe.
    """
    if kind not in ('post', 'event'):
        raise ValueError("kind debe ser 'post' o 'event'")
    uid = f"{profile_id}_{'post' if kind == 'post' else 'event'}"
    results = users_collection.get(ids=[uid], include=['embeddings'])
    embeddings = results.get('embeddings', [])
    if len(embeddings) == 0:
        return None
    return np.array(embeddings[0])


def upsert_user_vector(profile_id: str, vector: np.ndarray, kind: str = 'post'):
    """
    Upsert del vector de interés del usuario (post/event).
    """
    if kind not in ('post', 'event'):
        raise ValueError("kind debe ser 'post' o 'event'")
    uid = f"{profile_id}_{'post' if kind == 'post' else 'event'}"
    users_collection.upsert(
        ids=[uid],
        embeddings=[vector.tolist()],
        metadatas=[{"type": f"{kind}_interest"}]
    )