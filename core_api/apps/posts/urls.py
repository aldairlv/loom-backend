from django.urls import path
from .views import PostListView

app_name = 'posts'

urlpatterns = [
    # Cuando se acceda a la raíz de las URLs de esta app (que será /v1/posts/),
    # se llamará a nuestra PostListView.
    path('', PostListView.as_view(), name='post-list'),
]