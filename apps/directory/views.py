from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, ListView, UpdateView

from .forms import ProfileForm
from .models import ExpertiseTerm, Profile
from .services import (
    filter_public_profiles,
    get_featured_expertise_terms,
    get_public_profile_queryset,
)


class DirectoryListView(ListView):
    context_object_name = "profiles"
    model = Profile
    paginate_by = 12
    template_name = "directory/directory_list.html"

    def get_queryset(self):
        return filter_public_profiles(
            query=self.request.GET.get("q", "").strip(),
            expertise=self.request.GET.get("expertise", "").strip(),
            organization=self.request.GET.get("organization", "").strip(),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["featured_terms"] = get_featured_expertise_terms(limit=12)
        context["search_query"] = self.request.GET.get("q", "").strip()
        context["search_expertise"] = self.request.GET.get("expertise", "").strip()
        context["search_organization"] = self.request.GET.get("organization", "").strip()
        context["result_count"] = self.get_queryset().count()
        return context


class ProfileDetailView(DetailView):
    context_object_name = "profile"
    template_name = "directory/profile_detail.html"

    def get_queryset(self):
        return get_public_profile_queryset()

    def get_object(self, queryset=None):
        queryset = queryset or self.get_queryset()
        return queryset.get(public_id=self.kwargs["public_id"])


class ProfileEditView(LoginRequiredMixin, UpdateView):
    form_class = ProfileForm
    template_name = "directory/profile_form.html"

    def get_object(self, queryset=None):
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        return profile

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Your public profile has been updated.")
        return super().form_valid(form)

    def get_success_url(self):
        if self.object.is_public:
            return self.object.get_absolute_url()
        return reverse("accounts:account-home")


class ExpertiseSuggestionView(View):
    def get(self, request, *args, **kwargs):
        query = request.GET.get("q", "").strip()
        queryset = ExpertiseTerm.objects.all()
        if query:
            queryset = queryset.filter(name__icontains=query)
        suggestions = list(queryset.order_by("name").values_list("name", flat=True)[:8])
        return JsonResponse({"results": suggestions})
