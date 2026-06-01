import pytest
import numpy as np
from unittest.mock import patch
from fastapi.testclient import TestClient

import chromadb
import chromadb.errors
from app.services import embedder, chroma_service
from main import app
from app.core import database


@pytest.fixture(scope="session", autouse=True)
def mock_embedder_model(request):
    """
    Mockea el modelo de embedding para evitar cargarlo en las pruebas.
    Devuelve vectores predecibles basados en el input.
    Se salta si la prueba tiene el marcador 'integration'.
    """
    if 'integration' in request.keywords:
        yield
        return

    def mock_get_text_embedding(text: str) -> np.ndarray:
        # Devuelve un vector simple y predecible para el texto
        return np.full(512, 0.1)

    def mock_get_image_embedding(url: str) -> np.ndarray:
        # Devuelve un vector diferente para la imagen
        if "fail" in url:
            raise Exception("Mocked image download failure")
        return np.full(512, 0.9)

    with patch.object(embedder, 'get_text_embedding', side_effect=mock_get_text_embedding), \
         patch.object(embedder, 'get_image_embedding', side_effect=mock_get_image_embedding):
        # Aseguramos que el modelo se considere "cargado" para pasar las validaciones
        with patch.object(embedder, '_model', new="mocked_model"):
            yield


@pytest.fixture(scope="function")
def test_client():
    """
    Crea un cliente de prueba de API para cada prueba.
    - Limpia la colección ANTES de cada prueba para garantizar el aislamiento.
    """
    # 1. Obtener todos los documentos de la colección
    collection = database.posts_collection
    
    # 2. Si hay documentos, eliminarlos todos
    try:
        all_docs = collection.get()  # Obtiene todos los documentos
        if all_docs and all_docs.get("ids"):
            collection.delete(ids=all_docs["ids"])  # Elimina todos los documentos
    except Exception:
        # Si algo falla, simplemente continuar
        pass

    # 3. Retornar el cliente de prueba
    with TestClient(app) as client:
        yield client