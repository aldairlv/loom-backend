def test_get_recommendations(test_client):
    """
    Prueba el endpoint de recomendaciones.
    """
    # Indexar algunos posts
    test_client.post("/api/v1/index/post", json={"post_id": "rec-post-1", "text_content": "apple"})
    test_client.post("/api/v1/index/post", json={"post_id": "rec-post-2", "text_content": "banana"})
    test_client.post("/api/v1/index/post", json={"post_id": "rec-post-3", "image_urls": ["http://example.com/orange.jpg"]})

    # El vector de usuario es similar al de texto (0.1)
    user_vector = [0.15] * 512

    response = test_client.post(
        "/api/v1/recommendations/posts",
        json={
            "user_vector": user_vector,
            "exclude_ids": ["rec-post-2"], # Excluir uno de los posts
            "limit": 5
        }
    )

    assert response.status_code == 200
    data = response.json()
    
    # Debería recomendar 'rec-post-1' porque su vector (0.1) es el más cercano.
    # 'rec-post-3' (vector 0.9) es muy diferente.
    # 'rec-post-2' fue excluido.
    assert "recommended_posts" in data
    recommended_posts = data["recommended_posts"]
    recommended_ids = [item["post_id"] for item in recommended_posts]
    assert "rec-post-1" in recommended_ids
    assert "rec-post-2" not in recommended_ids


def test_get_recommendations_no_results(test_client):
    """Prueba que devuelva una lista vacía si no hay resultados."""
    # Vector de usuario muy diferente a todo lo indexado
    user_vector = [100.0] * 512
    response = test_client.post("/api/v1/recommendations/posts", json={"user_vector": user_vector, "limit": 5})

    assert response.status_code == 200
    assert response.json() == {"recommended_posts": []}