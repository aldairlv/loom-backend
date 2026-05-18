from rest_framework import viewsets, status
from rest_framework.response import Response
from profiles.models import Profile
from .models import Post
from .serializers import PostSerializer
from . import services
from drf_spectacular.utils import extend_schema



class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    
    def get_queryset(self):
        # Filtramos solo los que no están eliminados
        return Post.objects.filter(is_deleted=False).select_related('author').prefetch_related('tags', 'contents')

    def create(self, request, *args, **kwargs):
        # El serializador ahora espera 'contents_input' que es una lista de PostContentSerializer
        # con 'media_id' o 'text'
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Obtenemos el perfil principal del usuario que hace la petición.
        # Es más seguro y robusto que usar request.user.profile directamente.
        try:
            author_profile = request.user.profiles.get(is_default=True)
        except Profile.DoesNotExist:
            return Response({"error": "El usuario no tiene un perfil por defecto."}, status=status.HTTP_400_BAD_REQUEST)

        # 'contents' ahora viene de 'contents_input' en validated_data
        contents_data = serializer.validated_data.pop('contents', [])

        post = services.create_post(
            author=author_profile,
            data=serializer.validated_data, # Contiene status, parent, root, tags...
            contents_data=contents_data
        )
        
        return Response(PostSerializer(post).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        post = self.get_object()
        serializer = self.get_serializer(post, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        updated_post = services.update_post(post, serializer.validated_data)
        return Response(PostSerializer(updated_post).data)

    def destroy(self, request, *args, **kwargs):
        post = self.get_object()
        services.delete_post(post)
        return Response(status=status.HTTP_204_NO_CONTENT)