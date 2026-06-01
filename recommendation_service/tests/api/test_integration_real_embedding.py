# tests/api/test_integration_real_embedding.py
import pytest
import numpy as np

# ¡Importante! Marca todo el fichero como prueba de integración
pytestmark = pytest.mark.integration

def test_real_embedding_and_recommendation(test_client):
    """
    Prueba de integración de extremo a extremo:
    1. Indexa un post con contenido real, usando el modelo de embedding real.
    2. Usa el vector resultante de ese post como perfil de usuario.
    3. Pide recomendaciones y verifica que el post original es el resultado más similar.
    """
    # 1. Indexar un post con texto e imagen. Esto usará el modelo real.
    post_data = {
        "post_id": "real-post-integration",
        "tags": "tecnologia, codigo, python",
        "text_content": "El código limpio es una forma de arte.",
        "image_urls": ["https://http.cat/images/200.jpg"] # Una imagen real que funcione
    }
    response = test_client.post("/api/v1/index/post", json=post_data)
    assert response.status_code == 200
    print("Post real indexado correctamente.")

    # 2. Obtener el vector que se acaba de guardar en ChromaDB para usarlo como perfil
    from app.services import chroma_service
    vectors = chroma_service.get_vectors_by_ids(["real-post-integration"])
    assert len(vectors) == 1
    user_profile_vector = vectors[0]

    # Verificamos que el vector no es el mock (0.1 o 0.9)
    assert not np.allclose(user_profile_vector, 0.1)
    assert not np.allclose(user_profile_vector, 0.9)
    print(f"Vector real obtenido de ChromaDB. Media: {np.mean(user_profile_vector)}")

    # 3. Pedir recomendaciones usando este vector de perfil
    rec_response = test_client.post(
        "/api/v1/recommendations/posts",
        json={
            "user_vector": user_profile_vector.tolist(),
            "limit": 5
        }
    )
    assert rec_response.status_code == 200
    recommendations = rec_response.json()["recommended_posts"]
    assert recommendations[0]["post_id"] == "real-post-integration"

    # El resultado más similar a un vector debería ser él mismo.
    print("Recomendación correcta recibida.")
