import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.directory.models import ExpertiseTerm, Profile
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
    assert user.first_name == "Elena"
    assert user.last_name == "Editor"
    assert profile.organizational_entity == "Division 4.2"
    assert profile.location == Profile.Location.AH
    assert set(profile.expertise_terms.values_list("name", flat=True)) == {
        "X-ray diffraction",
        "additive manufacturing",
    }


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
