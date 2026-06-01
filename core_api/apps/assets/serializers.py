import uuid
from PIL import Image
import imageio
from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from .models import Media, MediaType


CONTENT_TYPE_EXTENSION_MAP = {
    'image/jpeg': 'jpg',
    'image/png': 'png',
    'video/mp4': 'mp4',
    'video/webm': 'webm',
    'audio/mpeg': 'mp3',
}


def generate_unique_filename(filename, content_type=None):
    """
    Genera un nombre único para el archivo usando UUID.
    Preserva la extensión original si está disponible, y si no
    utiliza el content_type para obtener la extensión adecuada.

    Ejemplo: 'miVideo.mp4' -> 'a1b2c3d4-e5f6-7890-abcd-ef1234567890.mp4'
    """
    ext = ''
    if filename and '.' in filename:
        ext = filename.rsplit('.', 1)[-1].lower()

    if not ext and content_type:
        ext = CONTENT_TYPE_EXTENSION_MAP.get(content_type.lower(), '')

    unique_id = uuid.uuid4()
    return f'{unique_id}.{ext}' if ext else str(unique_id)

class MediaSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)
    # Sobrescribimos 'url' para asegurarnos de que siempre sea una URL absoluta en la salida.
    url = serializers.SerializerMethodField()

    class Meta:
        model = Media
        fields = ['id', 'url', 'type', 'width', 'height', 'file']
        # 'url' ya no es read_only aquí porque lo maneja get_url
        read_only_fields = ['id', 'type', 'width', 'height']

    @extend_schema_field(serializers.URLField)
    def get_url(self, obj: Media) -> str | None:
        """Construye y devuelve la URL absoluta para el archivo multimedia."""
        request = self.context.get('request')
        if request and obj.url:
            return request.build_absolute_uri(obj.url)
        return None

    def create(self, validated_data):
        uploaded_file = validated_data.pop('file')
        original_filename = uploaded_file.name
        content_type = uploaded_file.content_type

        # Generar nombre único con UUID, usando la extensión del filename
        # cuando está disponible, o bien la inferida desde content_type.
        unique_filename = generate_unique_filename(original_filename, content_type)

        # Guardar el archivo en el storage configurado.
        uploaded_file.seek(0)
        saved_path = default_storage.save(unique_filename, uploaded_file)

        media_type_value = content_type
        width, height = 0, 0

        if 'image' in content_type:
            if 'jpeg' in content_type:
                media_type_value = MediaType.IMAGE_JPEG.value
            elif 'png' in content_type:
                media_type_value = MediaType.IMAGE_PNG.value
            else:
                media_type_value = content_type
            try:
                uploaded_file.seek(0)
                img = Image.open(uploaded_file)
                width, height = img.size
            except Exception:
                pass
        elif 'video' in content_type:
            if 'mp4' in content_type:
                media_type_value = MediaType.VIDEO_MP4.value
            elif 'webm' in content_type:
                media_type_value = MediaType.VIDEO_WEBM.value
            try:
                video_path = default_storage.path(saved_path)
                video_reader = imageio.get_reader(video_path)
                width, height = video_reader.get_meta_data()['size']
                video_reader.close()
            except Exception:
                pass
        elif 'audio' in content_type:
            if 'mpeg' in content_type:
                media_type_value = MediaType.AUDIO_MP3.value

        media_instance = Media.objects.create(
            url=f"{settings.MEDIA_URL}{saved_path}",
            type=media_type_value,
            width=width,
            height=height,
            original_filename=original_filename,
        )
        return media_instance
