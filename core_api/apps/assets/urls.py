from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MediaViewSet

app_name = 'assets'

# Creamos un router
router = DefaultRouter()

# Registramos el ViewSet para Media
router.register(r'media', MediaViewSet, basename='media')

urlpatterns = [
    path('', include(router.urls)),
]