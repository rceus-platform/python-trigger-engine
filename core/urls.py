from django.urls import path

from . import views
from .views import daily_recall

urlpatterns = [
    path("", views.health_check, name="health"),
    path("process-reel/", views.process_reel),
    path("recall/daily/", daily_recall),
]
