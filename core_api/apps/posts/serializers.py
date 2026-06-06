from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from assets.serializers import MediaSerializer
from assets.models import Media
from .models import Tag, PostContent, Post
from profiles.models import Profile
from interactions.models import Like, PostComment
from interactions.serializers import LikeSerializer
from relationships.models import Follow
from .fields import TagRelatedField # Importamos nuestro nuevo campo

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'is_trending']


class ContentInputSerializer(serializers.Serializer):
    """
    Serializer para validar la entrada de 'contents' de forma polimórfica.
    El objeto JSON de entrada cambia según el 'type'.
    """
    type = serializers.CharField()
    text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    media_id = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, data):
        """
        Validación a nivel de objeto para asegurar que los campos correctos
        estén presentes según el 'type'.
        """
        content_type = data.get('type')
        # Si el tipo es 'text', el campo 'text' no debe ser nulo.
        # Se permite una cadena vacía ("") para representar, por ejemplo, un salto de línea.
        if content_type == 'text' and data.get('text') is None:
            raise serializers.ValidationError({"text": "Para el tipo 'text', el campo 'text' es requerido y no puede ser nulo."})
        if content_type in ['image', 'video', 'audio'] and not data.get('media_id'):
            raise serializers.ValidationError({"media_id": f"El tipo '{content_type}' requiere un 'media_id'."})
        
        return data


class PostContentSerializer(serializers.ModelSerializer):
    # Serializamos media anidado para lectura, pero permitimos el ID para escritura
    media = MediaSerializer(read_only=True) # Para mostrar el objeto media en GET
    media_id = serializers.PrimaryKeyRelatedField(
        queryset=Media.objects.all(), source='media', write_only=True, required=False, allow_null=True
    )
    # Revertimos el campo 'upload'
    # upload = serializers.FileField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = PostContent
        # 'media_id' es para la entrada (write), 'media' es para la salida (read)
        fields = ['id', 'type', 'order', 'text', 'media', 'media_id']
        # Hacemos 'type' y 'order' escribibles
        read_only_fields = ['id', 'media']


class PostAuthorSerializer(serializers.ModelSerializer):
    """
    Serializador simplificado para mostrar la información del autor de un post.
    """
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ['id', 'display_name', 'avatar_url', 'is_followed']

    is_followed = serializers.SerializerMethodField()

    @extend_schema_field(serializers.URLField)
    def get_avatar_url(self, obj: Profile) -> str | None:
        request = self.context.get('request')
        if request and obj.get_avatar_url:
            return request.build_absolute_uri(obj.get_avatar_url)
        return obj.get_avatar_url

    def get_is_followed(self, obj: Profile) -> bool:
        """Si el request tiene usuario autenticado, devuelve si ese usuario sigue a `obj`."""
        request = self.context.get('request')
        if not request or not hasattr(request, 'user') or request.user.is_anonymous:
            return False
        try:
            from_profile = request.user.profile
        except Exception:
            return False
        return Follow.objects.filter(from_profile=from_profile, to_profile=obj).exists()


class ParentPostSerializer(serializers.ModelSerializer):
    """
    Serializador simplificado para mostrar la información del post padre.
    """
    author = PostAuthorSerializer(read_only=True)

    class Meta:
        model = Post
        fields = ['id', 'author']


class PostTrailSerializer(serializers.ModelSerializer):
    """Serializador para los elementos del trail de reblogs."""
    author = PostAuthorSerializer(read_only=True)
    contents = PostContentSerializer(many=True, read_only=True)

    class Meta:
        model = Post
        fields = ['id', 'author', 'contents', 'layout']


class RootPostSerializer(serializers.ModelSerializer):
    """
    Serializador simplificado para mostrar la información del post raíz (root).
    """
    author = PostAuthorSerializer(read_only=True)
    contents = PostContentSerializer(many=True, read_only=True)

    class Meta:
        model = Post
        fields = ['id', 'author', 'contents', 'layout']

class PostSerializer(serializers.ModelSerializer):
    # Relaciones anidadas
    contents = PostContentSerializer(many=True, read_only=True)
    
    # Para los tags, usamos slug para que sea más fácil enviar los nombres desde el frontend
    tags = TagRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        slug_field='name'
    )
    
    # Información del autor con avatar
    author = PostAuthorSerializer(read_only=True)
    # --- Campos para LECTURA (GET) ---
    # Muestran la información anidada del autor.
    parent = ParentPostSerializer(read_only=True)
    root_post = RootPostSerializer(source='root', read_only=True)
    trail = serializers.SerializerMethodField()
    interactions = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()

    # --- Campos para ESCRITURA (POST/PUT) ---
    # Permiten enviar solo el ID para crear la relación.
    parent_id = serializers.PrimaryKeyRelatedField(
        queryset=Post.objects.all(), source='parent', write_only=True, required=False, allow_null=True
    )
    root_id = serializers.PrimaryKeyRelatedField(
        queryset=Post.objects.all(), source='root', write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = Post
        fields = [
            'id', 'author', 'parent_id', 'root_id', 
            'status', 'tags', 'contents', 'layout',# 'show_trailing',
            'is_deleted', 'created_at', 'updated_at', 'published_at', 
            'parent', 'root_post', 'trail', 'interactions', 'stats', #'trail_ids'
        ]
        read_only_fields = [
            'id', 'author', 'contents', 'created_at', 'updated_at',
            'published_at', 'parent', 'root_post', 'trail', 'interactions', 'stats', 'trail_ids',
        ]

    def get_trail(self, obj):
        if not obj.trail_ids:
            return []

        order_map = {post_id: index for index, post_id in enumerate(obj.trail_ids)}
        posts = Post.objects.filter(id__in=obj.trail_ids).select_related('author').prefetch_related('contents__media')
        ordered_posts = sorted(posts, key=lambda post: order_map.get(post.id, 0))
        return PostTrailSerializer(ordered_posts, many=True, context=self.context).data

    def get_interactions(self, obj: Post) -> dict:
        """Devuelve las interacciones del usuario actual sobre el post."""
        request = self.context.get('request')
        result = {
            'liked': False,
            'reposted': False,
            'commented': False,
        }
        if not request or not hasattr(request, 'user') or request.user.is_anonymous:
            return result
        try:
            profile = request.user.profile
        except Exception:
            return result

        # Liked
        result['liked'] = Like.objects.filter(post=obj, profile=profile).exists()

        # Reposted: buscamos si existe un post del mismo profile que tenga a `obj` como root
        result['reposted'] = Post.objects.filter(root=obj, author=profile).exists()

        # Commented: si existe algún comentario no borrado de este profile en el post
        result['commented'] = PostComment.objects.filter(post=obj, profile=profile, is_deleted=False).exists()

        return result

    def get_stats(self, obj: Post) -> dict:
        """Agrega contadores relacionados con el post."""
        # likes: número de Like
        likes_count = obj.likes.count()
        # comments: solo comentarios que no estén marcados como borrados
        comments_count = obj.comments.filter(is_deleted=False).count()
        # reposts: número de posts que referencian este post como `root`
        reposts_count = Post.objects.filter(root=obj).count()
        return {
            'likes_count': likes_count,
            'reposts_count': reposts_count,
            'comments_count': comments_count,
        }


class PostCreateSerializer(serializers.ModelSerializer):
    """
    Serializer optimizado para la creación de Posts. Acepta un JSON limpio
    y polimórfico para los contenidos.
    """
    contents_input = ContentInputSerializer(many=True, write_only=True, required=True, source='contents')
    layout = serializers.JSONField(required=False, default=list)
    tags = TagRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        slug_field='name',
        required=False
    )
    parent_id = serializers.PrimaryKeyRelatedField(
        queryset=Post.objects.all(), source='parent', write_only=True, required=False, allow_null=True
    )
    root_id = serializers.PrimaryKeyRelatedField(
        queryset=Post.objects.all(), source='root', write_only=True, required=False, allow_null=True
    )
    show_trailing = serializers.BooleanField(required=False, default=True)

    class Meta:
        model = Post
        fields = ['parent_id', 'root_id', 'status', 'tags', 'contents_input', 'layout', 'show_trailing']

    def create(self, validated_data):
        # El servicio create_post ya maneja la lógica de parent/root y tags.
        # Solo necesitamos pasarle los datos en el formato que espera.
        # El 'create' del serializer se encarga de la creación de PostContent.
        contents_data = validated_data.pop('contents', [])
        
        # La lógica de creación del post y sus relaciones se delega al servicio.
        # Aquí solo preparamos los datos.
        # El servicio `create_post` se encargará de crear los PostContent.
        # Nota: El servicio `create_post` necesita ser actualizado para manejar esto.
        # Por ahora, implementamos la lógica aquí para ser directos.
        return super().create(validated_data)