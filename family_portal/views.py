"""SIEM-006 (Parent Record Access) and CNS-011 (Parent Messaging)."""
from __future__ import annotations

import json

from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from accounts.access import can_view_student, log_access
from accounts.decorators import client_ip, role_required
from academics.models import ClassSection, Student

from .forms import NewMessageForm, ReplyForm
from .models import Message, MessageThread

# ---- SIEM-006: Parent Record Access ----------------------------------------


def _children_for(user):
    return [s.parent_view() for s in Student.objects.filter(parents=user)]


def _load_child_record(request, student_id):
    """The filtered record, or None if this parent may not see it.

    A child that exists but belongs to someone else returns the same
    "not found" as one that doesn't exist at all, so a parent can't use the
    response to probe for valid student IDs.
    """
    student = Student.objects.filter(student_id=student_id).first()
    allowed = (
        student is not None and request.user.role == "parent"
        and can_view_student(request.user, student)
    )
    log_access(request.user, "view_child_records", student_id, allowed, client_ip(request))
    if not allowed:
        return None
    return {
        "student": student.parent_view(),
        "grades": [
            {"course": g.section.course.name, "assessment": g.assessment,
             "score": g.score, "max_score": g.max_score}
            for g in student.grades.select_related("section__course")
        ],
        "attendance": [
            {"date": a.date.isoformat(), "course": a.section.course.name, "status": a.status}
            for a in student.attendance_records.select_related("section__course")
        ],
    }


@role_required("parent")
def children_page(request):
    log_access(request.user, "list_children", None, True, client_ip(request))
    return render(request, "family_portal/parent_records.html",
                  {"children": _children_for(request.user), "record": None})


@role_required("parent")
def child_records_page(request, student_id):
    record = _load_child_record(request, student_id)
    if record is None:
        raise PermissionDenied("Record not found.")
    return render(request, "family_portal/parent_records.html",
                  {"children": _children_for(request.user), "record": record})


@role_required("parent")
def api_children(request):
    log_access(request.user, "list_children", None, True, client_ip(request))
    return JsonResponse({"success": True, "children": _children_for(request.user)})


@role_required("parent")
def api_child_records(request, student_id):
    record = _load_child_record(request, student_id)
    if record is None:
        return JsonResponse({"success": False, "message": "Record not found."}, status=404)
    return JsonResponse({"success": True, **record})


# ---- CNS-011: Parent Messaging ----------------------------------------------


def _recipient_choices(teacher):
    """(value, label) pairs for every parent of a student assigned to one
    of this teacher's sections. `value` packs parent id + student id so
    the form can validate both together, same as the Sprint 1 design."""
    seen = {}
    for section in ClassSection.objects.filter(teacher=teacher).prefetch_related("students__parents"):
        for student in section.students.all():
            for parent in student.parents.all():
                seen[(parent.pk, student.pk)] = f"{parent.username} (parent of {student.name})"
    return [(f"{parent_id}:{student_id}", label) for (parent_id, student_id), label in seen.items()]


@role_required("teacher", "parent")
def inbox_page(request):
    threads = (
        MessageThread.objects.filter(teacher=request.user) | MessageThread.objects.filter(parent=request.user)
    ).distinct().order_by("-created_at")
    return render(request, "family_portal/messages.html", {
        "threads": threads, "recipient_choices": _recipient_choices(request.user)
        if request.user.role == "teacher" else [], "thread": None, "error": None,
    })


def _thread_or_403(request, thread_id):
    thread = get_object_or_404(MessageThread, pk=thread_id)
    if request.user.pk not in (thread.teacher_id, thread.parent_id):
        raise PermissionDenied("Conversation not found.")
    return thread


@role_required("teacher", "parent")
def thread_page(request, thread_id):
    thread = _thread_or_403(request, thread_id)
    if request.method == "POST":
        form = ReplyForm(request.POST)
        if form.is_valid():
            Message.objects.create(thread=thread, sender=request.user, body=form.cleaned_data["body"])
            return redirect("family_portal:thread", thread_id=thread.pk)
    messages = thread.messages.select_related("sender")
    messages.filter(read_at__isnull=True).exclude(sender=request.user).update(read_at=timezone.now())
    return render(request, "family_portal/thread.html", {"thread": thread, "messages": messages})


@role_required("teacher")
def send_message(request):
    choices = _recipient_choices(request.user)
    if request.method == "POST":
        form = NewMessageForm(request.POST, recipient_choices=choices)
        if form.is_valid():
            parent_id, student_id = form.cleaned_data["recipient"].split(":")
            thread = MessageThread.objects.create(
                student_id=int(student_id), teacher=request.user, parent_id=int(parent_id),
                subject=form.cleaned_data["subject"],
            )
            Message.objects.create(thread=thread, sender=request.user, body=form.cleaned_data["body"])
            return redirect("family_portal:thread", thread_id=thread.pk)
    else:
        form = NewMessageForm(recipient_choices=choices)
    return render(request, "family_portal/send_message.html", {"form": form})


# ---- JSON API ---------------------------------------------------------------
def _json_body(request):
    return json.loads(request.body or b"{}")


@role_required("teacher", "parent")
def api_inbox(request):
    threads = (
        MessageThread.objects.filter(teacher=request.user) | MessageThread.objects.filter(parent=request.user)
    ).distinct().order_by("-created_at")
    return JsonResponse({"success": True, "threads": [
        {"thread_id": t.pk, "subject": t.subject, "student_id": t.student.student_id} for t in threads
    ]})


@require_http_methods(["POST"])
@role_required("teacher")
def api_send(request):
    payload = _json_body(request)
    parent_id, student_id = str(payload.get("recipient", "")), str(payload.get("student_id", ""))
    choices = {value for value, _ in _recipient_choices(request.user)}
    key = f"{parent_id}:{student_id}"
    if key not in choices:
        return JsonResponse(
            {"success": False, "message": "You can only message parents of your assigned students."},
            status=403,
        )
    thread = MessageThread.objects.create(
        student_id=int(student_id), teacher=request.user, parent_id=int(parent_id),
        subject=str(payload.get("subject", ""))[:120],
    )
    Message.objects.create(thread=thread, sender=request.user, body=str(payload.get("body", "")))
    return JsonResponse({"success": True, "thread_id": thread.pk}, status=201)


@role_required("teacher", "parent")
def api_thread(request, thread_id):
    thread = get_object_or_404(MessageThread, pk=thread_id)
    if request.user.pk not in (thread.teacher_id, thread.parent_id):
        return JsonResponse({"success": False, "message": "Conversation not found."}, status=404)
    return JsonResponse({"success": True, "messages": [
        {"from": m.sender.username, "body": m.body, "sent_at": m.sent_at.isoformat()}
        for m in thread.messages.select_related("sender")
    ]})


@require_http_methods(["POST"])
@role_required("teacher", "parent")
def api_reply(request, thread_id):
    thread = get_object_or_404(MessageThread, pk=thread_id)
    if request.user.pk not in (thread.teacher_id, thread.parent_id):
        return JsonResponse({"success": False, "message": "Conversation not found."}, status=404)
    body = str(_json_body(request).get("body", "")).strip()
    if not body:
        return JsonResponse({"success": False, "message": "Message body is required."}, status=400)
    message = Message.objects.create(thread=thread, sender=request.user, body=body)
    return JsonResponse({"success": True, "message_id": message.pk}, status=201)
