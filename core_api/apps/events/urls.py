from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import EventViewSet

app_name = 'events'

router = DefaultRouter()
router.register(r'events', EventViewSet, basename='event')

urlpatterns = [
    path('', include(router.urls)),
]