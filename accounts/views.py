"""UMA-002: Secure Login.

    - Build secure login UI          -> login_view (GET renders, POST authenticates)
    - Password complexity validation -> accounts/validators.py (via api_register)
    - Create authentication API      -> api_login / api_register
    - Enforce HTTPS for all traffic  -> config/settings.py (SecurityMiddleware)
    - Log failed login attempts      -> the "accounts.auth" logger below,
                                         plus lockout.py for repeated failures
"""
from __future__ import annotations

import json
import logging

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .decorators import client_ip
from .lockout import is_locked_out, record_failure, record_success
from .models import User

logger = logging.getLogger("accounts.auth")


def _max_attempts() -> int:
    from django.conf import settings

    return settings.MAX_FAILED_ATTEMPTS


def _window_seconds() -> int:
    from django.conf import settings

    return settings.LOCKOUT_WINDOW_MINUTES * 60


@require_http_methods(["GET", "POST"])
def login_view(request):
    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        ip = client_ip(request)

        if is_locked_out(username, _max_attempts(), _window_seconds()):
            logger.warning("LOGIN BLOCKED (lockout) user=%s ip=%s", username, ip)
            error = "Account temporarily locked due to repeated failed attempts."
        elif not username or not password:
            logger.warning("LOGIN FAILED (missing credentials) user=%s ip=%s", username or "?", ip)
            error = "Username and password are required."
        else:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                record_success(username)
                auth_login(request, user)
                logger.info("LOGIN SUCCESS user=%s ip=%s", username, ip)
                return redirect("accounts:dashboard")

            record_failure(username, _window_seconds())
            logger.warning("LOGIN FAILED (bad credentials) user=%s ip=%s", username, ip)
            error = "Invalid username or password."

    return render(request, "accounts/login.html", {"error": error})


@require_http_methods(["POST"])
def logout_view(request):
    auth_logout(request)
    return redirect("accounts:login")


@login_required
def dashboard(request):
    context = {"user": request.user}
    if request.user.role == User.Role.STUDENT:
        from academics.models import Student  # local import: avoids a hard

        context["own_student"] = Student.objects.filter(user=request.user).first()
    return render(request, "accounts/dashboard.html", context)


@require_http_methods(["POST"])
def api_login(request):
    payload = json.loads(request.body or b"{}")
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    ip = client_ip(request)

    if is_locked_out(username, _max_attempts(), _window_seconds()):
        logger.warning("LOGIN BLOCKED (lockout) user=%s ip=%s", username, ip)
        return JsonResponse(
            {"success": False, "locked_out": True,
             "message": "Account temporarily locked due to repeated failed attempts."},
            status=423,
        )

    if not username or not password:
        logger.warning("LOGIN FAILED (missing credentials) user=%s ip=%s", username or "?", ip)
        return JsonResponse(
            {"success": False, "locked_out": False, "message": "Username and password are required."},
            status=401,
        )

    user = authenticate(request, username=username, password=password)
    if user is not None:
        record_success(username)
        auth_login(request, user)
        logger.info("LOGIN SUCCESS user=%s ip=%s", username, ip)
        return JsonResponse({"success": True, "locked_out": False, "message": "Login successful."})

    record_failure(username, _window_seconds())
    logger.warning("LOGIN FAILED (bad credentials) user=%s ip=%s", username, ip)
    return JsonResponse(
        {"success": False, "locked_out": False, "message": "Invalid username or password."}, status=401
    )


@require_http_methods(["POST"])
def api_register(request):
    payload = json.loads(request.body or b"{}")
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    role = str(payload.get("role", User.Role.STUDENT))

    if not username:
        return JsonResponse({"success": False, "message": "Username is required."}, status=400)

    try:
        validate_password(password)
    except ValidationError as exc:
        return JsonResponse(
            {"success": False, "message": "Weak password.", "errors": exc.messages}, status=400
        )

    UserModel = get_user_model()
    if UserModel.objects.filter(username=username).exists():
        return JsonResponse(
            {"success": False, "message": f"User '{username}' already exists."}, status=409
        )

    if role not in User.Role.values:
        role = User.Role.STUDENT

    UserModel.objects.create_user(username=username, password=password, role=role)
    return JsonResponse({"success": True, "message": f"User '{username}' created."}, status=201)
