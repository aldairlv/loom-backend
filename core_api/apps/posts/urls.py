from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PostViewSet

app_name = 'posts'

# Creamos un router
router = DefaultRouter()
# Registramos nuestro ViewSet. 'posts' será el prefijo de la URL (ej: /api/v1/posts/)
router.register(r'posts', PostViewSet, basename='post')


urlpatterns = [
    path('', include(router.urls)),
]