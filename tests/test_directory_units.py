from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.directory.forms import ProfileForm
from apps.directory.models import AuditEvent, ExpertiseTerm, Profile
from apps.directory.services import (
    format_expertise_names,
    get_featured_expertise_terms,
    get_or_create_expertise_terms,
    get_public_profile_count,
    get_public_profile_queryset,
    normalize_expertise_name,
    parse_expertise_names,
    record_audit_event,
)
from apps.directory.templatetags.directory_expertise import (
    expertise_chip_query,
    expertise_chip_selected,
)

pytestmark = pytest.mark.django_db
User = get_user_model()
TEST_PASSWORD = "HighlySecurePass123!!"  # pragma: allowlist secret


def create_profile_user(
    *,
    email: str,
    public: bool = True,
    approved: bool = True,
    verified: bool = True,
):
    user = User.objects.create_user(
        email=email,
        password=TEST_PASSWORD,
        first_name="Test",
        last_name="User",
    )
    if verified:
        user.mark_email_verified()
    if approved:
        user.mark_approved()

    profile = user.profile
    profile.organizational_entity = "6.1"
    profile.job_title = "Scientist"
    profile.location = Profile.Location.UE
    profile.research_summary = "Studies BAM expertise."
    profile.is_public = public
    profile.save()
    return user, profile


def test_parse_expertise_names_strips_sorts_out_duplicates_and_empty_values():
    names = parse_expertise_names(" X-ray diffraction ; corrosion,\nCorrosion,,  tomography  ")

    assert names == ["X-ray diffraction", "corrosion", "tomography"]


def test_format_expertise_names_joins_values_for_query_strings():
    assert format_expertise_names(["Corrosion", "Tomography"]) == "Corrosion, Tomography"


def test_get_or_create_expertise_terms_reuses_existing_normalized_term():
    existing = ExpertiseTerm.objects.create(name="X-Ray Diffraction")
    terms = get_or_create_expertise_terms(["x-ray diffraction", "Corrosion"])
    corrosion_term = ExpertiseTerm.objects.get(name="Corrosion")

    assert [term.pk for term in terms] == [existing.pk, corrosion_term.pk]
    assert (
        ExpertiseTerm.objects.filter(
            normalized_name=normalize_expertise_name("x-ray diffraction")
        ).count()
        == 1
    )


def test_expertise_chip_query_adds_new_term_to_existing_filter():
    value = expertise_chip_query("Corrosion", "Tomography")

    assert value == "Corrosion, Tomography"


def test_expertise_chip_query_removes_term_when_clicked_again():
    value = expertise_chip_query("Corrosion, Tomography", "Tomography")

    assert value == "Corrosion"


def test_expertise_chip_selected_matches_case_insensitively():
    assert expertise_chip_selected("Corrosion, Tomography", "tomography") is True
    assert expertise_chip_selected("Corrosion", "Tomography") is False


def test_profile_submit_for_review_moves_draft_profile_to_pending_review():
    _, profile = create_profile_user(email="draft@bam.de")
    profile.moderation_status = Profile.ModerationStatus.DRAFT
    profile.has_pending_updates = False

    profile.submit_for_review(save=False)

    assert profile.moderation_status == Profile.ModerationStatus.PENDING_REVIEW
    assert profile.has_pending_updates is False
    assert profile.submitted_for_review_at is not None


def test_profile_submit_for_review_marks_pending_updates_for_published_profile():
    _, profile = create_profile_user(email="published@bam.de")
    profile.publish(save=True)

    profile.submit_for_review(save=False)

    assert profile.moderation_status == Profile.ModerationStatus.PUBLISHED
    assert profile.has_pending_updates is True


def test_profile_moderation_helpers_update_status_and_visibility():
    reviewer, profile = create_profile_user(email="moderation@bam.de")

    profile.publish(reviewed_by=reviewer, notes="Looks good.", save=False)
    assert profile.is_public is True
    assert profile.moderation_status == Profile.ModerationStatus.PUBLISHED
    assert profile.reviewed_by == reviewer
    assert profile.moderation_notes == "Looks good."

    profile.request_changes(reviewed_by=reviewer, notes="Please clarify.", save=False)
    assert profile.is_public is True
    assert profile.moderation_status == Profile.ModerationStatus.CHANGES_REQUESTED
    assert profile.has_pending_updates is False
    assert profile.moderation_notes == "Please clarify."

    profile.archive(reviewed_by=reviewer, notes="No longer public.", save=False)
    assert profile.is_public is False
    assert profile.moderation_status == Profile.ModerationStatus.ARCHIVED
    assert profile.archived_at is not None


def test_profile_form_requires_expertise_for_public_profile():
    user, profile = create_profile_user(email="public-form@bam.de")
    form = ProfileForm(
        instance=profile,
        user=user,
        data={
            "first_name": "Test",
            "last_name": "User",
            "organizational_entity": "6.1",
            "job_title": "Scientist",
            "location": Profile.Location.UE,
            "research_summary": "Studies BAM expertise.",
            "is_public": "on",
            "expertise_terms": "",
        },
    )

    assert not form.is_valid()
    assert form.errors["expertise_terms"] == [
        "Add at least one expertise term before publishing your profile."
    ]


def test_profile_form_staff_save_auto_publishes_profile():
    user = User.objects.create_superuser(
        email="staff-form@bam.de",
        password=TEST_PASSWORD,
        first_name="Staff",
        last_name="Reviewer",
    )
    profile = user.profile
    form = ProfileForm(
        instance=profile,
        user=user,
        data={
            "first_name": "Staff",
            "last_name": "Reviewer",
            "organizational_entity": "VP.1",
            "job_title": "Moderator",
            "location": Profile.Location.AH,
            "research_summary": "Helps colleagues find expertise.",
            "is_public": "on",
            "expertise_terms": "Simulations, Tomography",
        },
    )

    assert form.is_valid(), form.errors

    saved_profile = form.save()
    saved_profile.refresh_from_db()
    assert saved_profile.moderation_status == Profile.ModerationStatus.PUBLISHED
    assert saved_profile.has_pending_updates is False
    assert set(saved_profile.expertise_terms.values_list("name", flat=True)) == {
        "Simulations",
        "Tomography",
    }


def test_record_audit_event_links_actor_target_and_profile():
    actor, profile = create_profile_user(email="actor@bam.de")
    event = record_audit_event(
        actor=actor,
        target_user=actor,
        profile=profile,
        action=AuditEvent.Action.PROFILE_PUBLISHED,
        notes="Published for testing.",
    )

    assert event.actor == actor
    assert event.target_user == actor
    assert event.profile == profile
    assert event.notes == "Published for testing."


def test_get_public_profile_queryset_only_includes_verified_and_approved_profiles():
    _, visible_profile = create_profile_user(email="visible-queryset@bam.de")
    visible_profile.publish(save=True)

    _, hidden_profile = create_profile_user(email="hidden-queryset@bam.de", approved=False)
    hidden_profile.publish(save=True)

    queryset = get_public_profile_queryset()

    assert visible_profile in queryset
    assert hidden_profile not in queryset


@override_settings(ACCOUNT_REQUIRE_ADMIN_APPROVAL=False)
def test_get_public_profile_count_does_not_require_approval_when_disabled():
    _, profile = create_profile_user(email="count@bam.de", approved=False)
    profile.publish(save=True)

    assert get_public_profile_count() == 1


def test_get_featured_expertise_terms_counts_only_public_profiles():
    _, visible_profile = create_profile_user(email="featured-visible@bam.de")
    _, hidden_profile = create_profile_user(email="featured-hidden@bam.de", public=False)
    term = ExpertiseTerm.objects.create(name="Corrosion")
    visible_profile.expertise_terms.add(term)
    hidden_profile.expertise_terms.add(term)
    visible_profile.publish(save=True)
    hidden_profile.submit_for_review(save=True)

    featured = list(get_featured_expertise_terms(limit=5))

    assert featured[0].name == "Corrosion"
    assert featured[0].public_profile_count == 1


def test_profile_form_non_public_profile_can_save_without_expertise():
    user, profile = create_profile_user(email="private-form@bam.de", public=False)
    form = ProfileForm(
        instance=profile,
        user=user,
        data={
            "first_name": "Test",
            "last_name": "User",
            "organizational_entity": "6.1",
            "job_title": "Scientist",
            "location": Profile.Location.TTS,
            "research_summary": "Internal only.",
            "expertise_terms": "",
        },
    )

    assert form.is_valid(), form.errors

    saved_profile = form.save()
    saved_profile.refresh_from_db()
    assert saved_profile.moderation_status == Profile.ModerationStatus.DRAFT
    assert saved_profile.expertise_terms.count() == 0


def test_profile_publish_preserves_existing_publication_timestamp():
    _, profile = create_profile_user(email="published-at@bam.de")
    profile.publish(save=True)
    first_published_at = profile.published_at
    later_time = first_published_at + timedelta(days=1)

    with patch("apps.directory.models.timezone.now") as now_mock:
        now_mock.return_value = later_time
        profile.publish(save=False)

    assert profile.published_at == first_published_at
