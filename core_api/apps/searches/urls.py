from django.urls import path

from .views import AutocompleteView, ExploreSearchView

urlpatterns = [
    path('autocomplete/', AutocompleteView.as_view(), name='search-autocomplete'),
    path('explore/', ExploreSearchView.as_view(), name='search-explore'),
]
