from rest_framework.generics import ListAPIView
from django.db.models import Prefetch
from .models import Post, ContentBlock
from .serializers import PostSerializer


class PostListView(ListAPIView):
    """
    Una vista que devuelve una lista de todos los posts en formato JSON.
    """
    # 1. Definimos el Serializer que se usará para convertir los datos.
    serializer_class = PostSerializer

    # 2. Optimizamos la consulta a la base de datos.
    #    Esto es crucial para el rendimiento, ya que evita hacer cientos de
    #    consultas adicionales (problema N+1).
    queryset = Post.objects.select_related(
        # Corregimos 'blog' a 'blogId' para que coincida con el modelo.
        # Incluimos 'blogId__owner' para traer también el usuario en la misma consulta,
        # optimizando la obtención del 'username' en el serializer.
        'blogId__owner'
    ).prefetch_related(
        'tags',  # Trae todos los tags en una segunda consulta.
        # Trae todos los bloques de contenido y sus subtipos (texto/imagen)
        # en consultas adicionales eficientes.
        Prefetch(
            'content_blocks',
            queryset=ContentBlock.objects.select_related('textblock', 'imageblock')
        )
    )

    # ¡Y eso es todo! DRF se encarga del resto.