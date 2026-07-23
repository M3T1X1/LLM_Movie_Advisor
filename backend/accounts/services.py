from django.db import connection
from django.utils import timezone


def business_schema_available() -> bool:
    return "app_user" in connection.introspection.table_names()


def sync_business_user(user) -> dict:
    if not business_schema_available():
        return {
            "id": str(user.pk),
            "email": user.email,
            "username": user.get_username(),
            "dateJoined": user.date_joined.isoformat(),
            "isActive": user.is_active,
        }

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, email, username, date_joined, is_active
            FROM app_user
            WHERE username = %s OR email = %s
            ORDER BY (username = %s) DESC
            LIMIT 1
            """,
            [user.get_username(), user.email, user.get_username()],
        )
        row = cursor.fetchone()
        if row:
            cursor.execute(
                """
                UPDATE app_user
                SET email = %s, username = %s, password = %s, is_active = %s
                WHERE id = %s
                RETURNING id, email, username, date_joined, is_active
                """,
                [user.email, user.get_username(), user.password, user.is_active, row[0]],
            )
        else:
            cursor.execute(
                """
                INSERT INTO app_user (
                    email, username, password, date_joined, is_active
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, email, username, date_joined, is_active
                """,
                [
                    user.email,
                    user.get_username(),
                    user.password,
                    user.date_joined or timezone.now(),
                    user.is_active,
                ],
            )
        business_row = cursor.fetchone()
        cursor.execute(
            """
            INSERT INTO user_profile (
                user_id, semantic_summary, version, last_rebuilt_at, updated_at
            )
            VALUES (%s, NULL, 1, NULL, %s)
            ON CONFLICT (user_id) DO NOTHING
            """,
            [business_row[0], timezone.now()],
        )
    return {
        "id": str(business_row[0]),
        "email": business_row[1],
        "username": business_row[2],
        "dateJoined": business_row[3].isoformat(),
        "isActive": business_row[4],
    }


def get_business_user_id(user) -> int:
    return int(sync_business_user(user)["id"])
