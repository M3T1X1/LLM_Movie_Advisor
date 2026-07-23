from django.contrib import admin

from .models import (
    AgentExecution,
    BusinessUser,
    Content,
    Genre,
    Interaction,
    Message,
    RecommendationRequest,
    RecommendationRun,
    RunCandidate,
    UserPreference,
    UserProfile,
)


@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    list_display = ("title", "media_type", "release_date", "vote_average", "tmdb_id")
    list_filter = ("media_type",)
    search_fields = ("title", "original_title", "tmdb_id")
    readonly_fields = ("tmdb_refreshed_at",)


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("name", "tmdb_genre_id")
    search_fields = ("name",)


@admin.register(BusinessUser)
class BusinessUserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "is_active", "date_joined")
    search_fields = ("username", "email")
    exclude = ("password",)


@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = ("user", "content", "interaction_type", "rating", "created_at")
    list_filter = ("interaction_type",)
    search_fields = ("user__username", "content__title")


admin.site.register(UserProfile)
admin.site.register(UserPreference)
admin.site.register(Message)
admin.site.register(RecommendationRequest)
admin.site.register(RecommendationRun)
admin.site.register(RunCandidate)
admin.site.register(AgentExecution)
