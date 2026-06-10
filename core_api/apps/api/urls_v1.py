from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from accounts.views import EmailValidationView # Import the new view
from relationships.views import (
    MeFollowersView, MeFollowingView, MeFriendsView,
    UserFollowersView
)
from notifications.views import RegisterDeviceView

urlpatterns = [
    # Aquí agrupas las rutas por "temática"
    # Esto hará que la URL final sea /v2/timeline/dashboard
    path('posts/', include('posts.urls')),
    path('feeds/', include('feeds.urls')),
    path('assets/', include('assets.urls')),
    path('profiles/', include('profiles.urls')),
    path('interactions/', include('interactions.urls')),
    path('events/', include('events.urls')), # Nueva ruta para eventos
    path('relationships/', include('relationships.urls')),
    path('notifications/', include('notifications.urls')),
    path('chats/', include('chats.urls')),
    path('search/', include('searches.urls')),

    # NEW SEMANTIC ENDPOINTS (Better UX than /relationships/...)
    path('me/followers/', MeFollowersView.as_view(), name='api-me-followers'),
    path('me/following/', MeFollowingView.as_view(), name='api-me-following'),
    path('me/friends/', MeFriendsView.as_view(), name='api-me-friends'),
    path('users/<uuid:user_id>/followers/', UserFollowersView.as_view(), name='api-user-followers'),
    path('devices/', RegisterDeviceView.as_view(), name='register-device-main'),

    # Rutas de autenticación automática
    path('auth/', include('dj_rest_auth.urls')),
    path('auth/registration/', include('dj_rest_auth.registration.urls')),
    path('auth/email/validate/', EmailValidationView.as_view(), name='email_validate'), # New endpoint

    # Rutas de Swagger
    path('schema/', SpectacularAPIView.as_view(), name='schema'), # El archivo de definición
    path('swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'), # Interfaz visual
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'), # Otra alternativa visual
]