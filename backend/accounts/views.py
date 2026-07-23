import json

from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST


def _request_data(request: HttpRequest) -> dict | None:
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _user_data(user) -> dict:
    return {
        "id": str(user.pk),
        "email": user.email,
        "username": user.get_username(),
    }


@require_GET
@ensure_csrf_cookie
def csrf(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"detail": "CSRF cookie set."})


@require_POST
def login(request: HttpRequest) -> JsonResponse:
    data = _request_data(request)
    if data is None:
        return JsonResponse({"detail": "Invalid JSON body."}, status=400)

    email = data.get("email")
    password = data.get("password")
    if not isinstance(email, str) or not isinstance(password, str):
        return JsonResponse({"detail": "Email and password are required."}, status=400)

    normalized_email = email.strip().lower()
    if not normalized_email or not password:
        return JsonResponse({"detail": "Email and password are required."}, status=400)

    user_model = get_user_model()
    user = user_model.objects.filter(email__iexact=normalized_email).first()
    authenticated_user = (
        authenticate(request, username=user.get_username(), password=password)
        if user is not None
        else None
    )

    if authenticated_user is None:
        return JsonResponse({"detail": "Invalid email or password."}, status=401)

    django_login(request, authenticated_user)
    return JsonResponse({"user": _user_data(authenticated_user)})


@require_GET
def session(request: HttpRequest) -> JsonResponse:
    if not request.user.is_authenticated:
        return JsonResponse({"authenticated": False, "user": None})

    return JsonResponse(
        {
            "authenticated": True,
            "user": _user_data(request.user),
        }
    )


@require_POST
def logout(request: HttpRequest) -> JsonResponse:
    django_logout(request)
    return JsonResponse({"detail": "Logged out."})
