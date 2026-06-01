from django.urls import path
from .views import (
    FollowCreateView, UnfollowAPIView, FollowersListView, FollowingListView, FriendsListView,
)

app_name = 'relationships'

urlpatterns = [
    # ============ LEGACY ENDPOINTS ============
    # These are maintained for backwards compatibility but are DEPRECATED.
    # New clients should use the semantic endpoints:
    #   - POST   /api/v1/users/<user_id>/followers/        (instead of follow/)
    #   - DELETE /api/v1/users/<user_id>/followers/        (instead of unfollow/)
    #   - GET    /api/v1/me/followers/                     (instead of followers/)
    #   - GET    /api/v1/me/following/                     (instead of following/)
    #   - GET    /api/v1/me/friends/                       (instead of friends/)
    
    # POST /v1/relationships/follow/
    path('follow/', FollowCreateView.as_view(), name='follow'),
    # DELETE /v1/relationships/unfollow/<uuid:profile_id>/
    path('unfollow/<uuid:profile_id>/', UnfollowAPIView.as_view(), name='unfollow'),
    # GET /v1/relationships/followers/
    path('followers/', FollowersListView.as_view(), name='followers-list'),
    # GET /v1/relationships/following/
    path('following/', FollowingListView.as_view(), name='following-list'),
    # GET /v1/relationships/friends/
    path('friends/', FriendsListView.as_view(), name='friends-list'),
]