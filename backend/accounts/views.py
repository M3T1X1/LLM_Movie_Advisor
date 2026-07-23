import json

from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .services import sync_business_user


def _request_data(request: HttpRequest) -> dict | None:
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _user_data(user) -> dict:
    return sync_business_user(user)


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


@require_POST
def register(request: HttpRequest) -> JsonResponse:
    data = _request_data(request)
    if data is None:
        return JsonResponse({"detail": "Invalid JSON body."}, status=400)

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    if not all(isinstance(value, str) for value in (username, email, password)):
        return JsonResponse(
            {"detail": "Username, email and password are required."},
            status=400,
        )

    normalized_username = username.strip()
    normalized_email = email.strip().lower()
    if not normalized_username or not normalized_email or not password:
        return JsonResponse(
            {"detail": "Username, email and password are required."},
            status=400,
        )

    user_model = get_user_model()
    if user_model.objects.filter(username__iexact=normalized_username).exists():
        return JsonResponse({"detail": "Username is already in use."}, status=409)
    if user_model.objects.filter(email__iexact=normalized_email).exists():
        return JsonResponse({"detail": "Email is already in use."}, status=409)

    candidate = user_model(username=normalized_username, email=normalized_email)
    try:
        validate_password(password, user=candidate)
        candidate.full_clean(exclude=["password"])
    except ValidationError as error:
        return JsonResponse({"detail": " ".join(error.messages)}, status=400)

    try:
        with transaction.atomic():
            candidate.set_password(password)
            candidate.save()
            user_data = _user_data(candidate)
            django_login(request, candidate)
    except IntegrityError:
        return JsonResponse(
            {"detail": "Username or email is already in use."},
            status=409,
        )
    return JsonResponse({"user": user_data}, status=201)


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
