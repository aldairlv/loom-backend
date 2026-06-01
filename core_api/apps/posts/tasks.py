# core_api/apps/posts/tasks.py
from celery import shared_task
import requests
from .models import Post  # Importa tu modelo real de Posts

@shared_task(bind=True, max_retries=3, ignore_result=True)
def initialize_user_in_recommendation_service_task(self, profile_id):
    """
    Inicializa al usuario en la colección 'chroma_users' del servicio de recomendaciones
    cuando se crea un perfil. Se ejecuta de manera asíncrona mediante Celery.
    """
    try:
        url = "http://recommendation_service:8080/api/v1/users/create"
        payload = {
            "profile_id": str(profile_id),
        }
        
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        
        result = response.json()
        return f"Usuario {profile_id} inicializado en Chroma: {result.get('status', 'unknown')}"
        
    except requests.RequestException as e:
        # Si el servicio de recomendaciones está saturado o caído, Celery reintenta en 60 segundos
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3, ignore_result=True)
def indexar_post_task(self, post_id):
    """
    Esta tarea corre en segundo plano en el contenedor 'celery_worker'.
    Saca el post de Postgres y le avisa al recommendation_service por HTTP.
    """
    try:
        post = Post.objects.get(id=post_id)
        
        # Recolecta texto e imágenes del post para el servicio de recomendaciones.
        text_fragments = []
        image_urls = []
        for content in post.contents.all():
            if content.type == 'text' and content.text:
                text_fragments.append(content.text)
            if content.type == 'image' and content.media and content.media.url:
                image_urls.append(content.media.url)

        text_content = "\n\n".join(text_fragments).strip() if text_fragments else None
        tags = ", ".join(post.tags.values_list('name', flat=True)) if post.tags.exists() else None

        if not text_content and not image_urls:
            return f"Post {post_id} no tiene texto ni imágenes para indexar."

        url = "http://recommendation_service:8080/api/v1/index/post"
        payload = {
            "post_id": str(post.id),
            "tags": tags,
            "text_content": text_content,
            "image_urls": image_urls or None,
        }

        # Llamamos al microservicio síncronamente desde el Worker
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()

        result = response.json()
        return f"Post {post_id} indexado: {result.get('status', 'unknown')}"
        
    except Post.DoesNotExist:
        return f"El post {post_id} fue eliminado antes de procesarse."
    except requests.RequestException as e:
        # Si tu servicio de IA está saturado o caído, Celery reintenta en 60 segundos
        raise self.retry(exc=e, countdown=60)