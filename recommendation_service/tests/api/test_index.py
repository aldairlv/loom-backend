def test_index_post_text_only(test_client):
    """Prueba indexar un post que solo tiene contenido de texto y tags."""
    response = test_client.post(
        "/api/v1/index/post",
        json={"post_id": "post1", "tags": "test, python", "text_content": "Hello world"}
    )
    assert response.status_code == 200
    assert response.json() == {"id": "post1", "status": "indexed"}


def test_index_post_with_images(test_client):
    """Prueba indexar un post con texto y múltiples imágenes."""
    response = test_client.post(
        "/api/v1/index/post",
        json={
            "post_id": "post2",
            "tags": "images, art",
            "text_content": "Check out these images",
            "image_urls": ["https://http.cat/images/401.jpg", "https://http.cat/images/502.jpg"]
        }
    )
    assert response.status_code == 200
    assert response.json() == {"id": "post2", "status": "indexed"}


def test_index_post_no_content(test_client):
    """Prueba que la API devuelva un error si no hay contenido para indexar."""
    response = test_client.post(
        "/api/v1/index/post",
        json={"post_id": "post3"}
    )
    assert response.status_code == 400
    assert "debe tener al menos texto o una URL de imagen" in response.json()["detail"]


def test_index_post_image_failure(test_client):
    """Prueba que la indexación continúe si una URL de imagen falla."""
    response = test_client.post(
        "/api/v1/index/post",
        json={"post_id": "post4", "text_content": "Text with a bad image", "image_urls": ["http://example.com/fail.jpg"]}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "indexed"