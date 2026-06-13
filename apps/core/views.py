"""Lightweight core views shared across the application."""

from django.http import JsonResponse

from apps.directory.views import DirectoryListView


class HomeView(DirectoryListView):
    """Alias the root URL to the directory landing page."""

    pass


def health_view(request):
    """Return a minimal health response for containers and load balancers."""

    return JsonResponse({"status": "ok"})
