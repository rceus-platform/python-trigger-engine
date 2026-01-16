from django.urls import path

from . import views

urlpatterns = [
    path("", views.ui_home, name="ui_home"),
    path("api/health/", views.health_check, name="health"),
    path("api/process-reel/", views.process_reel),
    path("api/recall/daily/", views.daily_recall),
]
