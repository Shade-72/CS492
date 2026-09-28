"""Role-based access control (RBAC), consolidating three different
attempts from the original repo: Carmen O'Brien's FastAPI ROLE_MATRIX +
`check_role()` (TaskID5), her JWT `admin_required` dependency ("Restrict
critical alerts to admins only"), and the ad hoc `if role == "admin"`
checks scattered through Keiana Henry's and Alex Dominguez's Flask routes.
One decorator, used the same way by every app.
"""
from functools import wraps
import logging

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

access_logger = logging.getLogger("accounts.access")


def client_ip(request) -> str:
    return request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "unknown"))


def role_required(*roles: str):
    """Restrict a view to users whose `.role` is one of `roles`.

    Wraps `login_required`, so an anonymous user is redirected to the login
    page (or gets a plain 401 for an /api/ path); an authenticated user with
    the wrong role gets a 403, and the denial is logged.
    """

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.role not in roles:
                access_logger.warning(
                    "ACCESS DENIED (role) user=%s role=%s path=%s ip=%s",
                    request.user.username, request.user.role, request.path, client_ip(request),
                )
                raise PermissionDenied("You do not have permission to do that.")
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
