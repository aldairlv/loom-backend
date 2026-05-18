from fastapi import FastAPI
from pydantic import BaseModel
from core.chroma_manager import collection
from core.model_loader import get_model
from typing import List, Optional

app = FastAPI()

class LikeUpdate(BaseModel):
    user_id: int
    post_id: str
    current_vector: Optional[List[float]] = None # Especificamos que es una lista de floats

# 1. Agrega este nuevo modelo
class RecommendRequest(BaseModel):
    user_vector: List[float]
    exclude_ids: List[str]  # O List[int] según uses en Chroma
    limit: int = 3

@app.post("/update-interests")
async def update_interests(data: LikeUpdate):
    # Lógica de cálculo de nuevo vector (70/30)
    # Devuelve el nuevo vector a Django para que lo guarde en el perfil
    res = collection.get(ids=[data.post_id], include=['embeddings'])
    nuevo_vector = res['embeddings'][0]
    
    if data.current_vector:
        final = [(a * 0.0) + (p * 1.0) for a, p in zip(data.current_vector, nuevo_vector)]
    else:
        final = nuevo_vector
        
    return {"new_vector": final}

@app.post("/recommend")
# 2. Cambia la función para que use el modelo
async def get_recommendations(data: RecommendRequest):
    results = collection.query(
        query_embeddings=[data.user_vector],
        n_results=data.limit + len(data.exclude_ids),
        where={"id": {"$nin": data.exclude_ids}}
    )
    
    # Filtramos manualmente por si Chroma devuelve algo del exclude_ids 
    # (a veces el filtrado 'where' en Chroma tiene comportamientos inesperados)
    return {"ids": results['ids'][0][:data.limit]}