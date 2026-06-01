from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PostViewSet, TagViewSet

app_name = 'posts'

# Creamos un router
router = DefaultRouter()
# Registramos nuestro ViewSet. 'posts' será el prefijo de la URL (ej: /api/v1/posts/)
router.register(r'', PostViewSet, basename='post')
router.register(r'tags', TagViewSet, basename='tag')


urlpatterns = [
    path('', include(router.urls)),
]