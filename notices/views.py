"""CNS-010: "Admin can create/edit/delete announcements, students/teachers
can view, only admins can modify." CNS-012: "Only admins can send critical
alerts, access logged."

Replaces the Flask TASK14 snippet and the FastAPI `admin_required` JWT
dependency ("Restrict critical alerts to admins only") with one
`role_required("admin")` decorator (accounts/decorators.py) used for both.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import client_ip, role_required
from accounts.access import log_access

from .forms import AnnouncementForm, CriticalNotificationForm
from .models import Announcement, CriticalNotification


@login_required
def announcement_list(request):
    return render(request, "notices/announcement_list.html", {
        "announcements": Announcement.objects.all(),
    })


@role_required("admin")
def announcement_create(request):
    if request.method == "POST":
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.created_by = request.user
            announcement.save()
            return redirect("notices:announcement_list")
    else:
        form = AnnouncementForm()
    return render(request, "notices/announcement_form.html", {"form": form, "mode": "Create"})


@role_required("admin")
def announcement_edit(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)
    if request.method == "POST":
        form = AnnouncementForm(request.POST, instance=announcement)
        if form.is_valid():
            form.save()
            return redirect("notices:announcement_list")
    else:
        form = AnnouncementForm(instance=announcement)
    return render(request, "notices/announcement_form.html", {"form": form, "mode": "Edit"})


@role_required("admin")
def announcement_delete(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)
    if request.method == "POST":
        announcement.delete()
        return redirect("notices:announcement_list")
    return render(request, "notices/announcement_confirm_delete.html", {"announcement": announcement})


@login_required
def critical_notification_list(request):
    return render(request, "notices/critical_notification_list.html", {
        "notifications": CriticalNotification.objects.all(),
    })


@role_required("admin")
def critical_notification_create(request):
    if request.method == "POST":
        form = CriticalNotificationForm(request.POST)
        if form.is_valid():
            notification = form.save(commit=False)
            notification.created_by = request.user
            notification.save()
            log_access(request.user, "send_critical_notification", None, True, client_ip(request))
            return redirect("notices:critical_notification_list")
    else:
        form = CriticalNotificationForm()
    return render(request, "notices/critical_notification_form.html", {"form": form})
