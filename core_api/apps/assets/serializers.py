import uuid
from PIL import Image
from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework import serializers

from .models import Media, MediaType

class MediaSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)

    class Meta:
        model = Media
        fields = ['id', 'url', 'type', 'width', 'height', 'file']
        read_only_fields = ['id', 'url', 'type', 'width', 'height']

    def create(self, validated_data):
        uploaded_file = validated_data.pop('file')
        file_name = f"{uuid.uuid4().hex}_{uploaded_file.name}"

        # Guardar el archivo en el storage configurado.
        uploaded_file.seek(0)
        saved_path = default_storage.save(file_name, uploaded_file)

        content_type = uploaded_file.content_type
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
        elif 'audio' in content_type:
            if 'mpeg' in content_type:
                media_type_value = MediaType.AUDIO_MP3.value

        media_instance = Media.objects.create(
            url=f"{settings.MEDIA_URL}{saved_path}",
            type=media_type_value,
            width=width,
            height=height,
        )
        return media_instance
