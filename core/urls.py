from django.urls import path

from . import views
from .views import daily_recall, home

urlpatterns = [
    path("", home),
    path("health/", views.health_check, name="health"),
    path("process-reel/", views.process_reel),
    path("recall/daily/", daily_recall),
]
