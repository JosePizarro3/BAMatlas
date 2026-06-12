from django.contrib.auth import views as auth_views
from django.urls import path

from .forms import EmailAuthenticationForm
from .views import (
    AccountHomeView,
    RegisterView,
    RegistrationPendingView,
    ResendVerificationEmailView,
    VerifyEmailView,
)

app_name = "accounts"

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(
            authentication_form=EmailAuthenticationForm,
            template_name="registration/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
    path("register/", RegisterView.as_view(), name="register"),
    path("register/pending/", RegistrationPendingView.as_view(), name="registration-pending"),
    path("verify/resend/", ResendVerificationEmailView.as_view(), name="resend-verification"),
    path("verify/<uidb64>/<token>/", VerifyEmailView.as_view(), name="verify-email"),
    path("", AccountHomeView.as_view(), name="account-home"),
]
