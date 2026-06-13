from django.http import JsonResponse

from apps.directory.views import DirectoryListView


class HomeView(DirectoryListView):
    pass


def health_view(request):
    return JsonResponse({"status": "ok"})
