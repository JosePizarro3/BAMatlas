"""URL routes for the public directory and moderation dashboard."""

from django.urls import path

from .views import (
    DirectoryListView,
    ExpertiseSuggestionView,
    ModerationDashboardView,
    ProfileDetailView,
    ProfileEditView,
)

app_name = "directory"

urlpatterns = [
    path("", DirectoryListView.as_view(), name="list"),
    path("moderation/", ModerationDashboardView.as_view(), name="moderation-dashboard"),
    path("people/<uuid:public_id>/", ProfileDetailView.as_view(), name="profile-detail"),
    path("profile/edit/", ProfileEditView.as_view(), name="profile-edit"),
    path("expertise/suggest/", ExpertiseSuggestionView.as_view(), name="expertise-suggest"),
]
