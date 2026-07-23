from django.urls import path

from . import views


app_name = "api"

urlpatterns = [
    path("bootstrap/", views.bootstrap, name="bootstrap"),
    path("contents/", views.contents, name="contents"),
    path("contents/upcoming/", views.upcoming_contents, name="upcoming-contents"),
    path("recommendation-trends/", views.recommendation_trends, name="trends"),
    path("profile/", views.profile, name="profile"),
    path("conversations/", views.conversations, name="conversations"),
    path(
        "conversations/<int:conversation_id>/",
        views.conversation_detail,
        name="conversation-detail",
    ),
    path(
        "conversations/<int:conversation_id>/messages/",
        views.conversation_messages,
        name="conversation-messages",
    ),
    path("interactions/", views.interactions, name="interactions"),
    path(
        "interactions/<int:interaction_id>/",
        views.interaction_detail,
        name="interaction-detail",
    ),
]
