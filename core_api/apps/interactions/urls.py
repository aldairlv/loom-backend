from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PostCommentViewSet, EventCommentViewSet, BookmarkViewSet

app_name = 'interactions'

router = DefaultRouter()
router.register(r'post-comments', PostCommentViewSet, basename='post-comment')
router.register(r'event-comments', EventCommentViewSet, basename='event-comment')
router.register(r'bookmarks', BookmarkViewSet, basename='bookmark')

urlpatterns = [
    path('', include(router.urls)),
]
