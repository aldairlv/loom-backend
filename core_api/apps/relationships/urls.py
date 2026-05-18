from django.urls import path
from .views import FollowCreateView, UnfollowAPIView, FollowersListView, FollowingListView, FriendsListView

app_name = 'relationships'

urlpatterns = [
    # POST /v1/relationships/follow/ -> Seguir a un perfil (body: {"to_profile_id": "..."})
    path('follow/', FollowCreateView.as_view(), name='follow'),
    # DELETE /v1/relationships/unfollow/<uuid:profile_id>/ -> Dejar de seguir a un perfil
    path('unfollow/<uuid:profile_id>/', UnfollowAPIView.as_view(), name='unfollow'),
    # GET /v1/relationships/followers/ -> Listar mis seguidores
    path('followers/', FollowersListView.as_view(), name='followers-list'),
    # GET /v1/relationships/following/ -> Listar a quienes sigo
    path('following/', FollowingListView.as_view(), name='following-list'),
    # GET /v1/relationships/friends/ -> Listar amigos (seguimiento mutuo)
    path('friends/', FriendsListView.as_view(), name='friends-list'),
]