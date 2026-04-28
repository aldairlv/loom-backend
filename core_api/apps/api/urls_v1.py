from django.urls import path, include

urlpatterns = [
    # Aquí agrupas las rutas por "temática"
    # Esto hará que la URL final sea /v2/timeline/dashboard
    path('timeline/', include('feed_engine.urls')), 
    path('posts/', include('posts.urls')), 
]