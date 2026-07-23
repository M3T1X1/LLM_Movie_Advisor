from django.db import connection
from django.utils import timezone

from backend.api.models import BusinessUser, UserProfile


def business_schema_available() -> bool:
    return "app_user" in connection.introspection.table_names()


def sync_business_user(user, *, business_user_id: int | None = None) -> dict:
    if not business_schema_available():
        return {
            "id": str(user.pk),
            "email": user.email,
            "username": user.get_username(),
            "dateJoined": user.date_joined.isoformat(),
            "isActive": user.is_active,
        }

    if business_user_id is not None:
        business_user = BusinessUser.objects.filter(pk=business_user_id).first()
    else:
        business_user = BusinessUser.objects.filter(
            username=user.get_username()
        ).first()
        if business_user is None:
            business_user = BusinessUser.objects.filter(email=user.email).first()
    if business_user is None:
        business_user = BusinessUser(date_joined=user.date_joined or timezone.now())
    business_user.email = user.email
    business_user.username = user.get_username()
    business_user.password = user.password
    business_user.is_active = user.is_active
    business_user.save()
    UserProfile.objects.get_or_create(
        user=business_user,
        defaults={"updated_at": timezone.now()},
    )
    return {
        "id": str(business_user.pk),
        "email": business_user.email,
        "username": business_user.username,
        "dateJoined": business_user.date_joined.isoformat(),
        "isActive": business_user.is_active,
    }


def get_business_user_id(user) -> int:
    return int(sync_business_user(user)["id"])
