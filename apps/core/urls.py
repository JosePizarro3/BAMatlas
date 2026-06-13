"""Root application routes."""

from django.urls import path

from .views import HomeView, health_view

app_name = "core"

urlpatterns = [
    path("healthz/", health_view, name="health"),
    path("", HomeView.as_view(), name="home"),
]
