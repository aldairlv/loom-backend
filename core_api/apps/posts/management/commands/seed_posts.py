import random
import time
import hashlib
from pathlib import Path
from django.core.files import File
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings
from blogs.models import Blog
from posts.models import Post, ImageBlock, TextBlock, ContentBlockType, Tag

# Obtiene el modelo de Usuario que estés usando
User = get_user_model()
# Obtenemos la ruta base del script para localizar los archivos de muestra de forma segura
BASE_DIR = Path(__file__).resolve().parent
SAMPLE_IMAGES_DIR = BASE_DIR.parent.parent / 'sample_images'

class Command(BaseCommand):
    help = 'Crea posts de prueba con bloques de imagen y texto para poblar la base de datos.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('🚀 Iniciando la creación de posts de prueba...'))

        # --- 1. Preparación: Obtener o crear usuario y blog ---
        # Usamos update_or_create para asegurar que el usuario exista con los datos deseados.
        user, created = User.objects.update_or_create(username='demouser', defaults={'email': 'demo@example.com'})
        if created:
            self.stdout.write(f"👤 Usuario 'demouser' creado.")
        
        blog, created = Blog.objects.update_or_create(
            name='my-demo-blog',
            owner=user,
            defaults={'title': 'Un Blog de Demostración'}
        )
        if created:
            self.stdout.write(f"📓 Blog 'my-demo-blog' creado.")

        # --- 2. Crear el primer post ---
        self.create_post_with_content(
            blog=blog, user=user,
            image_path='sample_images/image1.jpg',
            text_content='Este es el texto que acompaña a la primera imagen. ¡Qué paisaje tan increíble!',
            tags_list=['art', 'painting', 'cozy', 'plants', 'illustration'],
            likes=random.randint(50, 500),
            reposts=random.randint(10, 100),
            comments=random.randint(2, 20)
        )

        # --- 3. Crear el segundo post ---
        self.create_post_with_content(
            blog=blog, user=user,
            image_path='sample_images/image2.jpg',
            text_content='Y aquí tenemos el segundo post. El arte abstracto siempre inspira.',
            tags_list=['green', 'bedroom', 'calm', 'interior design'],
            likes=random.randint(50, 500),
            reposts=random.randint(10, 100),
            comments=random.randint(2, 20)
        )

        self.stdout.write(self.style.SUCCESS('✅ ¡Script finalizado! Se han creado los posts de prueba.'))

    def create_post_with_content(self, blog, user, image_path, text_content, tags_list=None, likes=0, reposts=0, comments=0):
        """
        Función de ayuda para crear un Post con un ImageBlock y un TextBlock.
        Usa update_or_create para ser idempotente.
        """
        # --- Verificación de la imagen de muestra ---
        source_path = Path(settings.BASE_DIR) / image_path
        if not source_path.exists():
            self.stdout.write(self.style.ERROR(f"  -> La imagen de muestra no se encontró en: {source_path}"))
            return

        # --- Creación del Post (o actualización si ya existe) ---
        # Generamos un ID determinista para que el script sea idempotente.
        # Usamos un hash para asegurar un ID numérico único y grande.
        id_seed = f"{user.username}-{image_path}"
        post_id = int(hashlib.sha256(id_seed.encode('utf-8')).hexdigest(), 16) % (10**16)

        post, created = Post.objects.update_or_create(
            id=post_id, # Clave para la idempotencia
            defaults={
                'blogId': blog,
                'timestamp': int(time.time()),
                'likes_count': likes,
                'reposts_count': reposts,
                'comments_count': comments,
            }
        )

        if created:
            self.stdout.write(f"  -> Creado Post con ID: {post.id}")
        else:
            self.stdout.write(self.style.WARNING(f"  -> Actualizado Post con ID: {post.id}"))

        # --- Creación del Bloque de Imagen ---
        image_name = source_path.name
        media_dest_dir = Path(settings.MEDIA_ROOT) / 'post_images'
        media_dest_dir.mkdir(parents=True, exist_ok=True) # Asegura que el directorio exista
        dest_path = media_dest_dir / image_name

        # Copiamos el archivo al directorio de media para que Django lo pueda servir.
        with source_path.open('rb') as f:
            django_file = File(f, name=image_name)
            # Guardamos el archivo en el destino. Si ya existe, se sobrescribe.
            with dest_path.open('wb') as dest_f:
                for chunk in django_file.chunks():
                    dest_f.write(chunk)

        image_url = f"http://192.168.0.247:9080/media/post_images/{image_name}" # -> /media/post_images/image1.jpg

        ImageBlock.objects.update_or_create(
            post=post,
            defaults={
                'type': ContentBlockType.IMAGE,
                'order': 0,
                'media': [{"type": "image/jpeg", "url": image_url, "width": 800, "height": 600}]
            }
        )

        # --- Creación del Bloque de Texto ---
        TextBlock.objects.update_or_create(
            post=post,
            order=1, # Este bloque va después de la imagen
            defaults={'type': ContentBlockType.TEXT, 'text': text_content}
        )

        # --- Añadir Tags al Post ---
        if tags_list:
            for tag_name in tags_list:
                tag, _ = Tag.objects.get_or_create(name=tag_name)
                post.tags.add(tag)

        self.stdout.write(f"     - Contenido y tags para Post {post.id} asegurados.")
