import re

from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse

from .models import Profile
from .services import parse_expertise_names, replace_profile_expertise


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    expertise_terms = forms.CharField(
        required=False,
        help_text=(
            "Use commas to separate terms. Existing expertise will autocomplete while you type."
        ),
        widget=forms.TextInput(
            attrs={
                "placeholder": "X-ray diffraction, corrosion, additive manufacturing",
                "data-expertise-suggestions": "multi",
            }
        ),
    )

    class Meta:
        model = Profile
        fields = (
            "organizational_entity",
            "job_title",
            "location",
            "research_summary",
            "is_public",
        )
        widgets = {
            "organizational_entity": forms.TextInput(attrs={"placeholder": "6.1"}),
            "job_title": forms.TextInput(attrs={"placeholder": "Research Scientist"}),
            "research_summary": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": (
                        "Short public summary of your work, facilities, or methods people "
                        "can contact you about."
                    ),
                }
            ),
        }
        labels = {
            "organizational_entity": "Department code",
            "is_public": "Show this profile in the public directory",
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["first_name"].initial = self.user.first_name
        self.fields["last_name"].initial = self.user.last_name
        self.fields["expertise_terms"].initial = ", ".join(
            self.instance.expertise_terms.order_by("name").values_list("name", flat=True)
        )
        self.fields["expertise_terms"].widget.attrs["data-autocomplete-url"] = reverse(
            "directory:expertise-suggest"
        )
        self.fields["location"].required = False
        self.fields["location"].choices = [("", "Select a BAM site")] + list(
            Profile.Location.choices
        )
        self.fields["organizational_entity"].help_text = (
            "Use the BAM department code, for example 6.1 or VP.1."
        )
        self.fields["is_public"].help_text = (
            "Turn this on when you want colleagues to find your profile in the directory."
        )
        self.order_fields(
            [
                "first_name",
                "last_name",
                "organizational_entity",
                "job_title",
                "location",
                "research_summary",
                "expertise_terms",
                "is_public",
            ]
        )

    def clean_first_name(self):
        value = self.cleaned_data["first_name"].strip()
        if not value:
            raise ValidationError("Enter a given name.")
        return value

    def clean_last_name(self):
        value = self.cleaned_data["last_name"].strip()
        if not value:
            raise ValidationError("Enter a family name.")
        return value

    def clean_organizational_entity(self):
        value = self.cleaned_data["organizational_entity"].strip()
        if not value:
            raise ValidationError("Enter a department code.")
        if not re.fullmatch(r"[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)+", value):
            raise ValidationError("Use a BAM department code such as 6.1 or VP.1.")
        return value

    def clean_expertise_terms(self):
        return parse_expertise_names(self.cleaned_data["expertise_terms"])

    def clean(self):
        cleaned_data = super().clean()
        expertise_terms = cleaned_data.get("expertise_terms") or []
        if cleaned_data.get("is_public") and not expertise_terms:
            self.add_error(
                "expertise_terms",
                "Add at least one expertise term before publishing your profile.",
            )
        return cleaned_data

    def save(self, commit=True):
        profile = super().save(commit=False)
        self.user.first_name = self.cleaned_data["first_name"]
        self.user.last_name = self.cleaned_data["last_name"]
        if commit:
            self.user.save(update_fields=["first_name", "last_name"])
            profile.user = self.user
            profile.save()
            replace_profile_expertise(
                profile,
                self.cleaned_data["expertise_terms"],
                created_by=self.user,
            )
            if self.user.is_staff:
                profile.publish(
                    reviewed_by=self.user,
                    notes="Auto-published by staff profile edit.",
                )
            else:
                profile.submit_for_review()
        return profile
