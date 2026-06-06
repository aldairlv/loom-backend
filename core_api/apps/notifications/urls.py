from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import NotificationViewSet, RegisterDeviceView

router = DefaultRouter()
router.register(r'', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
    path('devices/', RegisterDeviceView.as_view(), name='register-device'),
]
