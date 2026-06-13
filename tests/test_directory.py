import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.directory.models import AuditEvent, ExpertiseTerm, Profile
from apps.directory.services import normalize_expertise_name

User = get_user_model()
pytestmark = pytest.mark.django_db


def create_directory_user(
    *,
    email,
    first_name,
    last_name,
    approved=True,
    public=True,
    expertise=None,
    organization="Division 6.1",
    location=Profile.Location.UE,
    publish=True,
):
    user = User.objects.create_user(
        email=email,
        password="HighlySecurePass123!!",
        first_name=first_name,
        last_name=last_name,
    )
    user.mark_email_verified()
    if approved:
        user.mark_approved()
    profile = user.profile
    profile.organizational_entity = organization
    profile.job_title = "Research Scientist"
    profile.location = location
    profile.research_summary = "Works on advanced materials characterisation."
    profile.is_public = public
    profile.save()
    if expertise:
        for term_name in expertise:
            ExpertiseTerm.objects.get_or_create(
                normalized_name=normalize_expertise_name(term_name),
                defaults={"name": term_name, "is_user_generated": True, "created_by": user},
            )
        profile.expertise_terms.set(
            ExpertiseTerm.objects.filter(
                normalized_name__in=[normalize_expertise_name(name) for name in expertise]
            )
        )
    if public:
        profile.submit_for_review()
        if publish:
            profile.publish(reviewed_by=user)
    return user


def test_profile_is_created_for_new_users():
    user = User.objects.create_user(
        email="newperson@bam.de",
        password="HighlySecurePass123!!",
        first_name="New",
        last_name="Person",
    )

    assert Profile.objects.filter(user=user).exists()


def test_profile_edit_updates_public_data_and_creates_expertise_terms(client):
    user = create_directory_user(
        email="editor@bam.de",
        first_name="Edit",
        last_name="User",
        expertise=["Microscopy"],
        publish=False,
    )
    client.force_login(user)

    response = client.post(
        reverse("directory:profile-edit"),
        {
            "first_name": "Elena",
            "last_name": "Editor",
            "organizational_entity": "Division 4.2",
            "job_title": "Senior Scientist",
            "location": Profile.Location.AH,
            "research_summary": "Develops methods for diffraction and imaging.",
            "is_public": "on",
            "expertise_terms": "X-ray diffraction, additive manufacturing",
        },
    )

    user.refresh_from_db()
    profile = user.profile
    assert response.status_code == 302
    assert response.headers["Location"] == reverse("accounts:account-home")
    assert user.first_name == "Elena"
    assert user.last_name == "Editor"
    assert profile.organizational_entity == "Division 4.2"
    assert profile.location == Profile.Location.AH
    assert profile.moderation_status == Profile.ModerationStatus.PENDING_REVIEW
    assert set(profile.expertise_terms.values_list("name", flat=True)) == {
        "X-ray diffraction",
        "additive manufacturing",
    }


def test_published_profile_edit_flags_pending_updates_but_stays_public(client):
    user = create_directory_user(
        email="published-editor@bam.de",
        first_name="Public",
        last_name="Editor",
        expertise=["Microscopy"],
        publish=True,
    )
    client.force_login(user)

    response = client.post(
        reverse("directory:profile-edit"),
        {
            "first_name": "Public",
            "last_name": "Editor",
            "organizational_entity": "Division 4.2",
            "job_title": "Senior Scientist",
            "location": Profile.Location.AH,
            "research_summary": "Updated summary",
            "is_public": "on",
            "expertise_terms": "X-ray diffraction, microscopy",
        },
    )

    user.refresh_from_db()
    profile = user.profile
    assert response.status_code == 302
    assert response.headers["Location"] == profile.get_absolute_url()
    assert profile.moderation_status == Profile.ModerationStatus.PUBLISHED
    assert profile.has_pending_updates is True


def test_staff_profile_edit_is_auto_published_and_listed(client):
    staff = User.objects.create_superuser(
        email="moderator@bam.de",
        password="HighlySecurePass123!!",
        first_name="Mod",
        last_name="Erator",
    )
    client.force_login(staff)

    response = client.post(
        reverse("directory:profile-edit"),
        {
            "first_name": "Mod",
            "last_name": "Erator",
            "organizational_entity": "Division 7.1",
            "job_title": "Moderator",
            "location": Profile.Location.UE,
            "research_summary": "Runs simulation reviews.",
            "is_public": "on",
            "expertise_terms": "simulations",
        },
    )

    staff.refresh_from_db()
    profile = staff.profile
    assert response.status_code == 302
    assert response.headers["Location"] == profile.get_absolute_url()
    assert profile.moderation_status == Profile.ModerationStatus.PUBLISHED
    assert profile.has_pending_updates is False

    directory_response = client.get(reverse("directory:list"), {"expertise": "simulations"})
    assert b"moderator@bam.de" in directory_response.content


def test_profile_edit_rejects_unknown_location_code(client):
    user = create_directory_user(
        email="invalid-location@bam.de",
        first_name="Invalid",
        last_name="Location",
        expertise=["Microscopy"],
    )
    client.force_login(user)

    response = client.post(
        reverse("directory:profile-edit"),
        {
            "first_name": "Invalid",
            "last_name": "Location",
            "organizational_entity": "Division 4.2",
            "job_title": "Senior Scientist",
            "location": "BERLIN",
            "research_summary": "Develops methods for diffraction and imaging.",
            "is_public": "on",
            "expertise_terms": "X-ray diffraction",
        },
    )

    assert response.status_code == 200
    assert b"Select a valid choice" in response.content


def test_directory_list_only_shows_public_verified_profiles(client):
    create_directory_user(
        email="visible@bam.de",
        first_name="Visible",
        last_name="Person",
        expertise=["Corrosion"],
    )
    create_directory_user(
        email="hidden@bam.de",
        first_name="Hidden",
        last_name="Person",
        expertise=["Corrosion"],
        public=False,
    )

    response = client.get(reverse("directory:list"))

    assert response.status_code == 200
    assert b"Visible Person" in response.content
    assert b"visible@bam.de" in response.content
    assert b"UE" in response.content
    assert b"Hidden Person" not in response.content


def test_directory_filters_by_expertise_term(client):
    create_directory_user(
        email="xray@bam.de",
        first_name="Xray",
        last_name="Researcher",
        expertise=["X-ray diffraction"],
    )
    create_directory_user(
        email="corrosion@bam.de",
        first_name="Corrosion",
        last_name="Researcher",
        expertise=["Corrosion"],
    )

    response = client.get(reverse("directory:list"), {"expertise": "X-ray diffraction"})

    assert response.status_code == 200
    assert b"Xray Researcher" in response.content
    assert b"Corrosion Researcher" not in response.content


def test_featured_term_counts_only_include_published_profiles():
    create_directory_user(
        email="published-sim@bam.de",
        first_name="Published",
        last_name="Sim",
        expertise=["simulations"],
        publish=True,
    )
    create_directory_user(
        email="pending-sim@bam.de",
        first_name="Pending",
        last_name="Sim",
        expertise=["simulations"],
        publish=False,
    )

    from apps.directory.services import get_featured_expertise_terms

    term = next(
        item for item in get_featured_expertise_terms(limit=20) if item.name == "simulations"
    )
    assert term.public_profile_count == 1


def test_home_and_directory_show_consistent_featured_terms(client):
    for index in range(9):
        create_directory_user(
            email=f"researcher-{index}@bam.de",
            first_name=f"Researcher{index}",
            last_name="User",
            expertise=[f"Topic {index:02d}"],
        )

    staff = User.objects.create_superuser(
        email="moderator-home@bam.de",
        password="HighlySecurePass123!!",
        first_name="Mod",
        last_name="Erator",
    )
    client.force_login(staff)
    client.post(
        reverse("directory:profile-edit"),
        {
            "first_name": "Mod",
            "last_name": "Erator",
            "organizational_entity": "Division 7.1",
            "job_title": "Moderator",
            "location": Profile.Location.UE,
            "research_summary": "Keeps the directory healthy.",
            "is_public": "on",
            "expertise_terms": "Topic 99",
        },
    )
    client.logout()

    home_response = client.get(reverse("core:home"))
    directory_response = client.get(reverse("directory:list"))

    assert home_response.status_code == 200
    assert directory_response.status_code == 200
    assert b"Topic 99" in home_response.content
    assert b"Topic 99" in directory_response.content


def test_public_profile_detail_is_accessible_for_public_profile(client):
    user = create_directory_user(
        email="detail@bam.de",
        first_name="Detail",
        last_name="Owner",
        expertise=["Residual stress"],
    )

    response = client.get(user.profile.get_absolute_url())

    assert response.status_code == 200
    assert b"Detail Owner" in response.content
    assert b"detail@bam.de" in response.content
    assert b"Residual stress" in response.content


def test_staff_moderation_dashboard_can_publish_profile_and_record_audit_event(client):
    staff = User.objects.create_superuser(
        email="staff@bam.de",
        password="HighlySecurePass123!!",
    )
    user = create_directory_user(
        email="pending-profile@bam.de",
        first_name="Pending",
        last_name="Profile",
        expertise=["Residual stress"],
        publish=False,
    )
    client.force_login(user)
    client.post(
        reverse("directory:profile-edit"),
        {
            "first_name": "Pending",
            "last_name": "Profile",
            "organizational_entity": "Division 4.2",
            "job_title": "Scientist",
            "location": Profile.Location.UE,
            "research_summary": "Ready for review.",
            "is_public": "on",
            "expertise_terms": "Residual stress",
        },
    )
    user.refresh_from_db()
    assert user.profile.moderation_status == Profile.ModerationStatus.PENDING_REVIEW

    client.force_login(staff)
    response = client.post(
        reverse("directory:moderation-dashboard"),
        {
            "action": "publish-profile",
            "profile_id": user.profile.id,
            "notes": "Approved for publication.",
        },
        follow=True,
    )

    user.refresh_from_db()
    assert response.status_code == 200
    assert user.profile.moderation_status == Profile.ModerationStatus.PUBLISHED
    assert AuditEvent.objects.filter(
        action=AuditEvent.Action.PROFILE_PUBLISHED,
        target_user=user,
        profile=user.profile,
    ).exists()


def test_requested_changes_can_be_resubmitted_for_review(client):
    staff = User.objects.create_superuser(
        email="reviewer@bam.de",
        password="HighlySecurePass123!!",
    )
    user = create_directory_user(
        email="resubmit@bam.de",
        first_name="Resubmit",
        last_name="User",
        expertise=["Residual stress"],
        publish=False,
    )
    client.force_login(user)
    client.post(
        reverse("directory:profile-edit"),
        {
            "first_name": "Resubmit",
            "last_name": "User",
            "organizational_entity": "Division 4.2",
            "job_title": "Scientist",
            "location": Profile.Location.UE,
            "research_summary": "First version.",
            "is_public": "on",
            "expertise_terms": "Residual stress",
        },
    )

    client.force_login(staff)
    client.post(
        reverse("directory:moderation-dashboard"),
        {
            "action": "request-profile-changes",
            "profile_id": user.profile.id,
            "notes": "Please clarify the summary.",
        },
    )

    user.refresh_from_db()
    assert user.profile.moderation_status == Profile.ModerationStatus.CHANGES_REQUESTED
    assert user.profile.is_public is True

    client.force_login(user)
    response = client.post(
        reverse("directory:profile-edit"),
        {
            "first_name": "Resubmit",
            "last_name": "User",
            "organizational_entity": "Division 4.2",
            "job_title": "Scientist",
            "location": Profile.Location.UE,
            "research_summary": "Updated version with the requested clarification.",
            "is_public": "on",
            "expertise_terms": "Residual stress",
        },
    )

    user.refresh_from_db()
    assert response.status_code == 302
    assert response.headers["Location"] == reverse("accounts:account-home")
    assert user.profile.moderation_status == Profile.ModerationStatus.PENDING_REVIEW

    client.force_login(staff)
    dashboard = client.get(reverse("directory:moderation-dashboard"))

    assert dashboard.status_code == 200
    assert b"resubmit@bam.de" in dashboard.content


def test_moderation_dashboard_requires_staff(client):
    user = create_directory_user(
        email="member@bam.de",
        first_name="Member",
        last_name="User",
        expertise=["Corrosion"],
    )
    client.force_login(user)

    response = client.get(reverse("directory:moderation-dashboard"))

    assert response.status_code == 403


def test_expertise_suggestion_endpoint_returns_matches(client):
    create_directory_user(
        email="suggestions@bam.de",
        first_name="Suggest",
        last_name="Owner",
        expertise=["X-ray diffraction", "X-ray fluorescence"],
    )

    response = client.get(reverse("directory:expertise-suggest"), {"q": "x-ray"})

    assert response.status_code == 200
    assert response.json()["results"] == ["X-ray diffraction", "X-ray fluorescence"]
