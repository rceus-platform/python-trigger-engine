"""URL routes exposed by the core app."""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.ui_index, name="ui-index"),  # ROOT UI
    path("favicon.ico", views.favicon, name="favicon"),
    path("api/process-reel/", views.process_reel),
    path("api/recall/daily/", views.daily_recall),
]
