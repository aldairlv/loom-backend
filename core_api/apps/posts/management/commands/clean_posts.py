import shutil
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model
from blogs.models import Blog
from posts.models import Post

# Obtiene el modelo de Usuario que estés usando
User = get_user_model()

class Command(BaseCommand):
    help = 'Elimina los posts, blogs y usuarios de demostración creados por el script seed_posts.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('🧹 Iniciando la limpieza de datos de demostración...'))

        # --- 1. Eliminar el Blog de demostración ---
        # Al eliminar el blog, los posts asociados también se eliminarán en cascada
        # si la relación ForeignKey tiene `on_delete=models.CASCADE` (que es el default).
        deleted_blogs, _ = Blog.objects.filter(name='my-demo-blog').delete()
        if deleted_blogs > 0:
            self.stdout.write(self.style.SUCCESS(f"🗑️  Blog 'my-demo-blog' y sus posts asociados eliminados."))
        else:
            self.stdout.write(self.style.NOTICE("- No se encontró el blog 'my-demo-blog' para eliminar."))

        # --- 2. Eliminar el Usuario de demostración ---
        # Hacemos lo mismo para el usuario.
        deleted_users, _ = User.objects.filter(username='demouser').delete()
        if deleted_users > 0:
            self.stdout.write(self.style.SUCCESS(f"🗑️  Usuario 'demouser' eliminado."))
        else:
            self.stdout.write(self.style.NOTICE("- No se encontró el usuario 'demouser' para eliminar."))

        # --- 3. Limpiar los archivos de imagen copiados ---
        # Borrar los registros de la base de datos no elimina los archivos físicos.
        # Debemos hacerlo manualmente.
        media_images_dir = Path(settings.MEDIA_ROOT) / 'post_images'
        
        # Lista de imágenes que tu script de seed copia
        sample_images = ['image1.jpg', 'image2.jpg']

        if media_images_dir.exists():
            self.stdout.write(f"🖼️  Buscando imágenes de muestra en {media_images_dir}...")
            for image_name in sample_images:
                image_path = media_images_dir / image_name
                if image_path.exists():
                    image_path.unlink() # unlink() elimina el archivo
                    self.stdout.write(self.style.SUCCESS(f"   - Archivo '{image_name}' eliminado."))
        else:
            self.stdout.write(self.style.NOTICE(f"- El directorio de imágenes {media_images_dir} no existe, no hay nada que limpiar."))


        self.stdout.write(self.style.SUCCESS('✅ ¡Limpieza completada!'))

