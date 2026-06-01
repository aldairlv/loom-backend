import numpy as np

def test_recalculate_user_profile_new_user(test_client):
    """
    Prueba recalcular el perfil para un usuario nuevo (sin vector actual).
    El nuevo vector del perfil debe ser igual al vector del post.
    """
    # Primero, indexamos un post para que exista su vector
    test_client.post("/api/v1/index/post", json={"post_id": "post-for-profile", "text_content": "some content"})

    response = test_client.post(
        "/api/v1/users/recalculate-profile",
        json={"post_id": "post-for-profile", "current_vector": None}
    )

    assert response.status_code == 200
    data = response.json()
    assert "new_vector" in data
    # El vector de texto mockeado es 0.1
    assert np.allclose(data["new_vector"], [0.1] * 512)


def test_recalculate_user_profile_existing_user(test_client):
    """
    Prueba la actualización del perfil de un usuario existente.
    El nuevo vector debe ser un promedio ponderado.
    """
    test_client.post("/api/v1/index/post", json={"post_id": "post-for-profile-2", "text_content": "other content"})

    current_vector = [0.5] * 512
    response = test_client.post(
        "/api/v1/users/recalculate-profile",
        json={"post_id": "post-for-profile-2", "current_vector": current_vector}
    )

    assert response.status_code == 200
    data = response.json()
    
    # Cálculo esperado: (current * 0.7) + (new * 0.3) -> (0.5 * 0.7) + (0.1 * 0.3) = 0.38
    expected_vector = (np.array(current_vector) * 0.7) + (np.full(512, 0.1) * 0.3)
    assert np.allclose(data["new_vector"], expected_vector)


def test_recalculate_profile_post_not_found(test_client):
    """Prueba que la API devuelva 404 si el post_id no existe."""
    response = test_client.post("/api/v1/users/recalculate-profile", json={"post_id": "non-existent-post"})
    assert response.status_code == 404
    assert "no se encontró" in response.json()["detail"]