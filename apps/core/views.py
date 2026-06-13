from django.views.generic import TemplateView

from apps.directory.services import (
    FEATURED_EXPERTISE_LIMIT,
    get_featured_expertise_terms,
    get_public_profile_count,
)


class HomeView(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["featured_terms"] = get_featured_expertise_terms(
            limit=FEATURED_EXPERTISE_LIMIT
        )
        context["public_profile_count"] = get_public_profile_count()
        return context
