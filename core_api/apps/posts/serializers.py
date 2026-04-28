from rest_framework import serializers
from .models import Post, Tag, ContentBlock, TextBlock, ImageBlock

# 1. Serializer sencillo para los Tags
class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['name']

# 2. Serializers específicos para cada tipo de bloque
class TextBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = TextBlock
        fields = ['type','text']

class ImageBlockSerializer(serializers.ModelSerializer):
    # Declaramos media como MethodField para poder manipular el JSON
    media = serializers.SerializerMethodField()

    class Meta:
        model = ImageBlock
        fields = ['type', 'media']

    def get_media(self, obj):
        request = self.context.get('request')
        media_data = obj.media  # Esto es tu lista [ {"url": "..."}, ... ]

        if media_data and request:
            for item in media_data:
                # Esta es la línea mágica que convierte la ruta relativa en absoluta.
                item['url'] = request.build_absolute_uri(item['url'])
        
        return media_data

# 3. Serializer "maestro" para bloques de contenido
class ContentBlockSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        # Capturamos el contexto que viene del PostSerializer
        context = self.context

        # Este método detecta si el bloque es de texto o imagen y usa el serializer correcto
        if hasattr(instance, 'textblock'):
            return TextBlockSerializer(instance.textblock, context=context).data
        elif hasattr(instance, 'imageblock'):
            return ImageBlockSerializer(instance.imageblock, context=context).data
        return super().to_representation(instance)

    class Meta:
        model = ContentBlock
        fields = ['id', 'type', 'order']

# 4. Serializer principal para el Post
class PostSerializer(serializers.ModelSerializer):
    # Para obtener el username, navegamos a través de las relaciones del modelo.
    # source='blogId.owner.username' le dice a DRF que vaya a:
    # Post -> blogId (el Blog) -> owner (el User) -> username (el campo del User)
    username = serializers.CharField(source='blogId.owner.username', read_only=True)

    # Traemos los tags como una lista de strings (nombres)
    tags = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')
    
    # Traemos los bloques de contenido relacionados
    # Usamos 'source' para que coincida con el 'related_name' del modelo ContentBlock
    content = ContentBlockSerializer(source='content_blocks', many=True, read_only=True)
    
    # Incluimos la property que definiste en el modelo
    # y la renombramos de 'notes_count' a 'notesCount'
    notesCount = serializers.ReadOnlyField(source='notes_count')

    # Renombramos los campos para que el JSON use camelCase
    likesCount = serializers.IntegerField(source='likes_count', read_only=True)
    repostsCount = serializers.IntegerField(source='reposts_count', read_only=True)
    commentsCount = serializers.IntegerField(source='comments_count', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)

    class Meta:
        model = Post
        fields = [
            'id', 'blogId', 'username', 'timestamp', 'layout', 'tags', 
            'content', 'likesCount', 'repostsCount', 
            'commentsCount', 'notesCount', 'createdAt', 'updatedAt'
        ]