from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import AuthenticationForm
from django import forms
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q

from .models import (
    AgentExecution,
    BusinessUser,
    Content,
    ContentEmbedding,
    ContentGenre,
    Conversation,
    Genre,
    Interaction,
    Message,
    RecommendationRequest,
    RecommendationRun,
    RunCandidate,
    UserPreference,
    UserProfile,
)


admin.site.site_header = "FilmiQ — panel administratora"
admin.site.site_title = "FilmiQ Admin"
admin.site.index_title = "Baza danych platformy"


class AdminEmailAuthenticationForm(AuthenticationForm):
    """Require an e-mail address while using Django's authentication backend."""

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request=request, *args, **kwargs)
        self.fields["username"] = forms.EmailField(
            label="Adres e-mail",
            max_length=254,
            widget=forms.EmailInput(
                attrs={
                    "autofocus": True,
                    "autocomplete": "email",
                    "placeholder": "admin@example.com",
                }
            ),
        )

    def clean(self):
        email = self.cleaned_data.get("username")
        if isinstance(email, str):
            user = get_user_model().objects.filter(
                email__iexact=email.strip()
            ).first()
            if user is None:
                raise ValidationError(
                    self.error_messages["invalid_login"],
                    code="invalid_login",
                    params={"username": "adres e-mail"},
                )
            self.cleaned_data["username"] = user.get_username()
        return super().clean()


admin.site.login_form = AdminEmailAuthenticationForm


def model_field_names(model: type[models.Model]) -> tuple[str, ...]:
    """Return editable concrete and many-to-many model fields."""
    return tuple(
        field.name
        for field in model._meta.get_fields()
        if (
            (field.concrete and not field.auto_created)
            or field.many_to_many
        )
    )


class NoManualCreateAdmin(admin.ModelAdmin):
    """Shared policy: records are created by the application, not the admin."""

    actions = None

    def has_add_permission(self, request):
        return False


class ReadOnlyBusinessAdmin(NoManualCreateAdmin):
    """Read-only technical data with a usable detail page."""

    def get_readonly_fields(self, request, obj=None):
        return model_field_names(self.model)

    def has_delete_permission(self, request, obj=None):
        return False


class DeletableReadOnlyAdmin(ReadOnlyBusinessAdmin):
    """Read-only fields, while explicit deletion remains available."""

    def has_delete_permission(self, request, obj=None):
        return admin.ModelAdmin.has_delete_permission(
            self,
            request,
            obj,
        )


def set_accounts_active(queryset, *, active: bool) -> int:
    """Keep auth_user and app_user activation flags synchronized."""
    usernames = list(queryset.values_list("username", flat=True))
    emails = list(queryset.values_list("email", flat=True))
    with transaction.atomic():
        updated = queryset.update(is_active=active)
        if queryset.model is BusinessUser:
            get_user_model().objects.filter(
                Q(username__in=usernames) | Q(email__in=emails)
            ).update(is_active=active)
        else:
            BusinessUser.objects.filter(
                Q(username__in=usernames) | Q(email__in=emails)
            ).update(is_active=active)
    return updated


def activate_users(modeladmin, request, queryset):
    updated = set_accounts_active(queryset, active=True)
    modeladmin.message_user(request, f"Aktywowano konta: {updated}.")


activate_users.short_description = "Aktywuj wybrane konta"


def deactivate_users(modeladmin, request, queryset):
    updated = set_accounts_active(queryset, active=False)
    modeladmin.message_user(request, f"Dezaktywowano konta: {updated}.")


deactivate_users.short_description = "Dezaktywuj wybrane konta"


@admin.register(BusinessUser)
class BusinessUserAdmin(NoManualCreateAdmin):
    list_display = ("id", "username", "email", "is_active", "date_joined")
    list_filter = ("is_active", "date_joined")
    search_fields = ("username", "email")
    ordering = ("-date_joined",)
    actions = (activate_users, deactivate_users)
    fields = ("id", "username", "email", "is_active", "date_joined")
    readonly_fields = ("id", "username", "email", "date_joined")

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        with transaction.atomic():
            super().save_model(request, obj, form, change)
            get_user_model().objects.filter(
                Q(username=obj.username) | Q(email=obj.email)
            ).update(is_active=obj.is_active)


@admin.register(UserProfile)
class UserProfileAdmin(ReadOnlyBusinessAdmin):
    list_display = ("user", "version", "last_rebuilt_at", "updated_at")
    search_fields = ("user__username", "user__email", "semantic_summary")
    list_select_related = ("user",)


@admin.register(UserPreference)
class UserPreferenceAdmin(ReadOnlyBusinessAdmin):
    list_display = (
        "id",
        "user",
        "preference_type",
        "preference_value",
        "polarity",
        "weight",
        "confidence",
    )
    list_filter = ("preference_type", "polarity")
    search_fields = (
        "user__username",
        "user__email",
        "preference_type",
        "preference_value",
    )
    list_select_related = ("user",)


@admin.register(Conversation)
class ConversationAdmin(DeletableReadOnlyAdmin):
    list_display = ("id", "title", "user", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("title", "user__username", "user__email")
    list_select_related = ("user",)
    ordering = ("-updated_at",)


@admin.register(Message)
class MessageAdmin(ReadOnlyBusinessAdmin):
    list_display = (
        "id",
        "conversation",
        "role",
        "sequence_no",
        "short_content",
        "created_at",
    )
    list_filter = ("role", "created_at")
    search_fields = ("content", "conversation__title", "conversation__user__username")
    list_select_related = ("conversation",)
    ordering = ("-created_at",)

    @admin.display(description="Treść")
    def short_content(self, obj):
        return obj.content if len(obj.content) <= 100 else f"{obj.content[:97]}..."


@admin.register(RecommendationRequest)
class RecommendationRequestAdmin(ReadOnlyBusinessAdmin):
    list_display = ("id", "conversation", "trigger_message", "mood", "created_at")
    list_filter = ("mood", "created_at")
    search_fields = ("conversation__title", "conversation__user__username", "mood")
    list_select_related = ("conversation", "trigger_message")
    ordering = ("-created_at",)


@admin.register(RecommendationRun)
class RecommendationRunAdmin(ReadOnlyBusinessAdmin):
    list_display = (
        "id",
        "request",
        "status",
        "model_name",
        "started_at",
        "finished_at",
    )
    list_filter = ("status", "model_name")
    search_fields = (
        "model_name",
        "graph_version",
        "request__conversation__title",
        "request__conversation__user__username",
    )
    list_select_related = ("request",)
    ordering = ("-id",)


@admin.register(Content)
class ContentAdmin(DeletableReadOnlyAdmin):
    list_display = (
        "id",
        "title",
        "media_type",
        "release_date",
        "vote_average",
        "popularity",
        "tmdb_id",
    )
    list_filter = ("media_type", "release_date", "original_language")
    search_fields = ("title", "original_title", "=tmdb_id")
    ordering = ("-popularity",)
    actions = ("delete_selected",)

    def get_deleted_objects(self, objs, request):
        contents = list(objs)
        content_ids = [item.pk for item in contents]
        candidate_count = RunCandidate.objects.filter(
            content_id__in=content_ids
        ).count()
        interaction_count = Interaction.objects.filter(
            content_id__in=content_ids
        ).count()
        embedding_count = ContentEmbedding.objects.filter(
            content_id__in=content_ids
        ).count()
        relation_count = ContentGenre.objects.filter(
            content_id__in=content_ids
        ).count()
        deleted_objects = [f"{item.media_type}: {item.title}" for item in contents]
        related = (
            ("kandydaci rekomendacji", candidate_count),
            ("interakcje użytkowników", interaction_count),
            ("embeddingi", embedding_count),
            ("powiązania z gatunkami", relation_count),
        )
        deleted_objects.extend(
            f"{label}: {count}"
            for label, count in related
            if count
        )
        model_count = {
            Content._meta.verbose_name_plural: len(contents),
        }
        model_count.update(
            {label: count for label, count in related if count}
        )
        return deleted_objects, model_count, set(), []

    @staticmethod
    def _delete_with_history(queryset):
        content_ids = list(queryset.values_list("pk", flat=True))
        if not content_ids:
            return
        with transaction.atomic():
            Interaction.objects.filter(content_id__in=content_ids).delete()
            RunCandidate.objects.filter(content_id__in=content_ids).delete()
            Content.objects.filter(pk__in=content_ids).delete()

    def delete_model(self, request, obj):
        self._delete_with_history(Content.objects.filter(pk=obj.pk))

    def delete_queryset(self, request, queryset):
        self._delete_with_history(queryset)


@admin.register(Genre)
class GenreAdmin(ReadOnlyBusinessAdmin):
    list_display = ("id", "name", "tmdb_genre_id", "content_count")
    search_fields = ("name", "=tmdb_genre_id")
    ordering = ("name",)

    @admin.display(description="Liczba treści")
    def content_count(self, obj):
        return obj.contents.count()


@admin.register(ContentEmbedding)
class ContentEmbeddingAdmin(ReadOnlyBusinessAdmin):
    list_display = (
        "id",
        "content",
        "embedding_model",
        "model_version",
        "source_language",
        "updated_at",
    )
    list_filter = ("embedding_model", "model_version", "source_language")
    search_fields = ("content__title", "source_text_hash")
    list_select_related = ("content",)
    ordering = ("-updated_at",)


@admin.register(RunCandidate)
class RunCandidateAdmin(ReadOnlyBusinessAdmin):
    list_display = (
        "id",
        "run",
        "content",
        "status",
        "final_rank",
        "final_score",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = (
        "content__title",
        "run__request__conversation__title",
        "run__request__conversation__user__username",
    )
    list_select_related = ("run", "content")
    ordering = ("-created_at",)


@admin.register(Interaction)
class InteractionAdmin(DeletableReadOnlyAdmin):
    list_display = (
        "id",
        "user",
        "content",
        "interaction_type",
        "rating",
        "created_at",
    )
    list_filter = ("interaction_type", "created_at")
    search_fields = ("user__username", "user__email", "content__title")
    list_select_related = ("user", "content", "source_candidate")
    ordering = ("-created_at",)


@admin.register(AgentExecution)
class AgentExecutionAdmin(ReadOnlyBusinessAdmin):
    list_display = (
        "id",
        "run",
        "agent_type",
        "sequence_no",
        "status",
        "duration_ms",
        "started_at",
    )
    list_filter = ("agent_type", "status")
    search_fields = (
        "agent_type",
        "run__request__conversation__title",
        "run__request__conversation__user__username",
    )
    list_select_related = ("run",)
    ordering = ("-started_at", "-id")


AuthUser = get_user_model()
try:
    admin.site.unregister(AuthUser)
except admin.sites.NotRegistered:
    pass


@admin.register(AuthUser)
class SafeAuthUserAdmin(UserAdmin):
    """Django accounts without password hashes or privilege editing."""

    list_display = ("username", "email", "is_active", "date_joined", "last_login")
    list_filter = ("is_active", "date_joined", "last_login")
    search_fields = ("username", "email")
    ordering = ("-date_joined",)
    actions = (activate_users, deactivate_users)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "username",
                    "email",
                    "is_active",
                    "date_joined",
                    "last_login",
                )
            },
        ),
    )
    readonly_fields = ("username", "email", "date_joined", "last_login")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        with transaction.atomic():
            super().save_model(request, obj, form, change)
            BusinessUser.objects.filter(
                Q(username=obj.username) | Q(email=obj.email)
            ).update(is_active=obj.is_active)
