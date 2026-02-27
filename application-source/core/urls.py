"""URL routes exposed by the core app."""

from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.ui_index, name="ui-index"),  # ROOT UI
    path("gate/", views.auth_gateway, name="auth-gateway"),
    path("login/pin/", views.login_passcode, name="login-pin"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="core/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("favicon.ico", views.favicon, name="favicon"),
    path("api/process-reel/", views.process_reel),
    path("api/recall/daily/", views.daily_recall),
]
