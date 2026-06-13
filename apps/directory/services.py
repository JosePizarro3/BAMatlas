import re

from django.conf import settings
from django.db.models import Count, Prefetch, Q

FEATURED_EXPERTISE_LIMIT = 12


def clean_expertise_display_name(name: str) -> str:
    return " ".join(name.strip().split())


def normalize_expertise_name(name: str) -> str:
    return clean_expertise_display_name(name).casefold()


def parse_expertise_names(raw_value: str) -> list[str]:
    parts = re.split(r"[\n,;]+", raw_value or "")
    seen: dict[str, str] = {}
    for part in parts:
        cleaned = clean_expertise_display_name(part)
        if cleaned:
            seen.setdefault(normalize_expertise_name(cleaned), cleaned)
    return list(seen.values())


def get_or_create_expertise_terms(names: list[str], *, created_by=None):
    from .models import ExpertiseTerm

    terms = []
    for display_name in names:
        normalized_name = normalize_expertise_name(display_name)
        term = ExpertiseTerm.objects.filter(normalized_name=normalized_name).first()
        if term is None:
            term = ExpertiseTerm.objects.create(
                name=display_name,
                is_user_generated=True,
                created_by=created_by,
            )
        terms.append(term)
    return terms


def replace_profile_expertise(profile, names: list[str], *, created_by=None):
    terms = get_or_create_expertise_terms(names, created_by=created_by)
    profile.expertise_terms.set(terms)
    return terms


def get_public_profile_queryset():
    from .models import Profile

    queryset = Profile.objects.select_related("user").prefetch_related(
        Prefetch("expertise_terms")
    ).filter(
        is_public=True,
        moderation_status=Profile.ModerationStatus.PUBLISHED,
        user__is_active=True,
        user__is_email_verified=True,
    )
    if settings.ACCOUNT_REQUIRE_ADMIN_APPROVAL:
        queryset = queryset.filter(user__is_approved=True)
    return queryset


def filter_public_profiles(*, query: str = "", expertise: str = "", organization: str = ""):
    queryset = get_public_profile_queryset()

    if query:
        queryset = queryset.filter(
            Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(user__email__icontains=query)
            | Q(organizational_entity__icontains=query)
            | Q(job_title__icontains=query)
            | Q(location__icontains=query)
            | Q(research_summary__icontains=query)
            | Q(expertise_terms__name__icontains=query)
        )

    if expertise:
        queryset = queryset.filter(
            expertise_terms__normalized_name=normalize_expertise_name(expertise)
        )

    if organization:
        queryset = queryset.filter(organizational_entity__icontains=organization)

    return queryset.distinct()


def get_featured_expertise_terms(*, limit: int = FEATURED_EXPERTISE_LIMIT):
    from .models import ExpertiseTerm

    public_filter = Q(
        profiles__is_public=True,
        profiles__moderation_status="published",
        profiles__user__is_active=True,
        profiles__user__is_email_verified=True,
    )
    if settings.ACCOUNT_REQUIRE_ADMIN_APPROVAL:
        public_filter &= Q(profiles__user__is_approved=True)

    return (
        ExpertiseTerm.objects.annotate(
            public_profile_count=Count("profiles", filter=public_filter, distinct=True)
        )
        .filter(public_profile_count__gt=0)
        .order_by("-public_profile_count", "name")[:limit]
    )


def get_public_profile_count() -> int:
    return get_public_profile_queryset().count()


def record_audit_event(*, actor=None, target_user=None, profile=None, action, notes=""):
    from .models import AuditEvent

    return AuditEvent.objects.create(
        actor=actor,
        target_user=target_user,
        profile=profile,
        action=action,
        notes=notes,
    )
