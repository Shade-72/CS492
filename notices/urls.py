from django.urls import path

from . import views

app_name = "notices"

urlpatterns = [
    path("announcements/", views.announcement_list, name="announcement_list"),
    path("announcements/new/", views.announcement_create, name="announcement_create"),
    path("announcements/<int:pk>/edit/", views.announcement_edit, name="announcement_edit"),
    path("announcements/<int:pk>/delete/", views.announcement_delete, name="announcement_delete"),
    path("notifications/critical/", views.critical_notification_list, name="critical_notification_list"),
    path("notifications/critical/new/", views.critical_notification_create, name="critical_notification_create"),
]
