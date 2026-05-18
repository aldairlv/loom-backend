from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from assets.serializers import MediaSerializer
from assets.models import Media, MediaType
from .models import Tag, PostContent, Post
from .fields import TagRelatedField # Importamos nuestro nuevo campo

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'is_trending']

class PostContentSerializer(serializers.ModelSerializer):
    # Serializamos media anidado para lectura, pero permitimos el ID para escritura
    media = MediaSerializer(read_only=True) # Para mostrar el objeto media en GET
    media_id = serializers.PrimaryKeyRelatedField(
        queryset=Media.objects.all(), source='media', write_only=True, required=False
    )
    # Revertimos el campo 'upload'
    # upload = serializers.FileField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = PostContent
        # 'media_id' es para la entrada (write), 'media' es para la salida (read)
        fields = ['id', 'type', 'order', 'text', 'media', 'media_id']
        # Hacemos 'type' y 'order' escribibles
        read_only_fields = ['id', 'media']

class PostSerializer(serializers.ModelSerializer):
    # Relaciones anidadas
    # Para lectura, mostramos los contenidos completos.
    contents = PostContentSerializer(many=True, read_only=True)
    # Para escritura, definimos un campo que sí se mostrará en la entrada (write_only)
    contents_input = PostContentSerializer(many=True, write_only=True, required=False, source='contents')
    
    # Para los tags, usamos slug para que sea más fácil enviar los nombres desde el frontend
    tags = TagRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        slug_field='name'
    )
    
    # Información del autor (asumiendo que quieres mostrar el nombre)
    author_name = serializers.CharField(source='author.slug', read_only=True)
    # El autor se establece automáticamente en la vista, no se espera en la entrada.
    author = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Post
        fields = [
            'id', 'author', 'author_name', 'parent', 'root', 'contents_input', # 'contents_input' para la entrada
            'status', 'tags', 'contents', 'created_at',
            'updated_at', 'published_at'
        ]
        read_only_fields = ['id', 'author', 'created_at', 'updated_at', 'published_at']