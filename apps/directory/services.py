"""Directory service helpers shared by views, forms, and admin actions."""

import re

from django.conf import settings
from django.db.models import Count, Prefetch, Q

FEATURED_EXPERTISE_LIMIT = 12
EXPERTISE_SUGGESTION_LIMIT = 8
MAX_EXPERTISE_TERMS = 20
MAX_EXPERTISE_TERM_LENGTH = 255


def clean_expertise_display_name(name: str) -> str:
    """Collapse repeated whitespace while preserving the visible term text."""

    return " ".join(name.strip().split())


def normalize_expertise_name(name: str) -> str:
    """Normalise expertise terms for case-insensitive deduplication."""

    return clean_expertise_display_name(name).casefold()


def parse_expertise_names(raw_value: str) -> list[str]:
    """Split a free-text list of expertise names into unique cleaned items."""

    parts = re.split(r"[\n,;]+", raw_value or "")
    seen: dict[str, str] = {}
    for part in parts:
        cleaned = clean_expertise_display_name(part)
        if cleaned:
            seen.setdefault(normalize_expertise_name(cleaned), cleaned)
    return list(seen.values())


def format_expertise_names(names: list[str]) -> str:
    """Format expertise names for the query string and form field display."""

    return ", ".join(names)


def get_or_create_expertise_terms(names: list[str], *, created_by=None):
    """Resolve expertise display names into stored term objects."""

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
    """Replace the expertise terms attached to a profile."""

    terms = get_or_create_expertise_terms(names, created_by=created_by)
    profile.expertise_terms.set(terms)
    return terms


def get_public_profile_filter(*, prefix: str = "") -> Q:
    """Build the visibility filter used for public directory content."""

    from .models import Profile

    criteria = Q(
        **{
            f"{prefix}is_public": True,
            f"{prefix}moderation_status": Profile.ModerationStatus.PUBLISHED,
            f"{prefix}user__is_active": True,
            f"{prefix}user__is_email_verified": True,
        }
    )
    if settings.ACCOUNT_REQUIRE_ADMIN_APPROVAL:
        criteria &= Q(**{f"{prefix}user__is_approved": True})
    return criteria


def get_public_profile_queryset():
    """Return the queryset that powers every public-facing directory view."""

    from .models import Profile

    queryset = (
        Profile.objects.select_related("user")
        .prefetch_related(Prefetch("expertise_terms"))
        .filter(get_public_profile_filter())
    )
    return queryset.order_by("user__last_name", "user__first_name", "user__email")


def filter_public_profiles(*, expertise: str = ""):
    """Apply the expertise-only search used by the public directory UI."""

    queryset = get_public_profile_queryset()

    if expertise:
        expertise_names = parse_expertise_names(expertise)
        normalized_names = [normalize_expertise_name(name) for name in expertise_names]
        queryset = queryset.annotate(
            matched_expertise_count=Count(
                "expertise_terms",
                filter=Q(expertise_terms__normalized_name__in=normalized_names),
                distinct=True,
            )
        ).filter(matched_expertise_count=len(normalized_names))

    return queryset.distinct()


def get_public_expertise_terms(*, query: str = ""):
    """Return expertise terms that are attached to publicly visible profiles."""

    from .models import ExpertiseTerm

    queryset = ExpertiseTerm.objects.annotate(
        public_profile_count=Count(
            "profiles",
            filter=get_public_profile_filter(prefix="profiles__"),
            distinct=True,
        )
    ).filter(public_profile_count__gt=0)
    if query:
        queryset = queryset.filter(name__icontains=query)
    return queryset.order_by("-public_profile_count", "name")


def get_featured_expertise_terms(*, limit: int = FEATURED_EXPERTISE_LIMIT):
    """Return the most common expertise terms for the landing page chips."""

    return get_public_expertise_terms()[:limit]


def get_expertise_suggestions(
    *, query: str = "", limit: int = EXPERTISE_SUGGESTION_LIMIT
) -> list[str]:
    """Return autocomplete suggestions without leaking unpublished expertise terms."""

    return list(get_public_expertise_terms(query=query).values_list("name", flat=True)[:limit])


def get_public_profile_count() -> int:
    """Count publicly visible profiles for operational dashboards."""

    return get_public_profile_queryset().count()


def record_audit_event(*, actor=None, target_user=None, profile=None, action, notes=""):
    """Create an immutable-style moderation or account event record."""

    from .models import AuditEvent

    return AuditEvent.objects.create(
        actor=actor,
        target_user=target_user,
        profile=profile,
        action=action,
        notes=notes,
    )
