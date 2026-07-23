
from django.db import models
from django.utils import timezone
from pgvector.django import VectorField


class MediaType(models.TextChoices):
    MOVIE = "movie", "Film"
    TV = "tv", "Serial"


class MessageRole(models.TextChoices):
    USER = "user", "Użytkownik"
    ASSISTANT = "assistant", "Asystent"
    SYSTEM = "system", "System"


class RunStatus(models.TextChoices):
    PENDING = "pending", "Oczekuje"
    RUNNING = "running", "W toku"
    COMPLETED = "completed", "Zakończony"
    FAILED = "failed", "Nieudany"
    CANCELLED = "cancelled", "Anulowany"


class CandidateStatus(models.TextChoices):
    PENDING = "pending", "Oczekuje"
    SELECTED = "selected", "Wybrany"
    REJECTED = "rejected", "Odrzucony"


class AgentStatus(models.TextChoices):
    PENDING = "pending", "Oczekuje"
    RUNNING = "running", "W toku"
    SUCCESS = "success", "Sukces"
    FAILED = "failed", "Nieudany"


class InteractionType(models.TextChoices):
    DETAILS_OPENED = "details_opened", "Otwarto szczegóły"
    LIKED = "liked", "Polubiono"
    DISLIKED = "disliked", "Odrzucono"
    WATCHLISTED = "watchlisted", "Zapisano"
    WATCHED = "watched", "Obejrzano"
    RATED = "rated", "Oceniono"


class BusinessUser(models.Model):
    id = models.BigAutoField(primary_key=True)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=255, null=True, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "app_user"

    def __str__(self):
        return self.username


class UserProfile(models.Model):
    user = models.OneToOneField(
        BusinessUser,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="profile",
    )
    semantic_summary = models.TextField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    last_rebuilt_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "user_profile"


class UserPreference(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        BusinessUser,
        on_delete=models.CASCADE,
        related_name="preferences",
    )
    preference_type = models.CharField(max_length=100)
    preference_value = models.TextField()
    polarity = models.SmallIntegerField()
    weight = models.DecimalField(max_digits=4, decimal_places=3, default=1)
    confidence = models.DecimalField(max_digits=4, decimal_places=3, default=1)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "user_preference"
        unique_together = (("user", "preference_type", "preference_value"),)


class Conversation(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        BusinessUser,
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    title = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "conversation"

    def __str__(self):
        return self.title or f"Rozmowa {self.pk}"


class Message(models.Model):
    id = models.BigAutoField(primary_key=True)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=MessageRole.choices)
    content = models.TextField()
    sequence_no = models.PositiveIntegerField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "message"
        unique_together = (("conversation", "sequence_no"),)


class RecommendationRequest(models.Model):
    id = models.BigAutoField(primary_key=True)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="recommendation_requests",
    )
    trigger_message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triggered_requests",
    )
    mood = models.CharField(max_length=100, null=True, blank=True)
    extracted_context = models.JSONField(default=dict)
    constraints = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "recommendation_request"


class RecommendationRun(models.Model):
    id = models.BigAutoField(primary_key=True)
    request = models.ForeignKey(
        RecommendationRequest,
        on_delete=models.CASCADE,
        related_name="runs",
    )
    status = models.CharField(
        max_length=20,
        choices=RunStatus.choices,
        default=RunStatus.PENDING,
    )
    graph_version = models.CharField(max_length=100, null=True, blank=True)
    model_name = models.CharField(max_length=255, null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "recommendation_run"


class Genre(models.Model):
    id = models.BigAutoField(primary_key=True)
    tmdb_genre_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=100)

    class Meta:
        db_table = "genre"

    def __str__(self):
        return self.name


class Content(models.Model):
    id = models.BigAutoField(primary_key=True)
    tmdb_id = models.BigIntegerField()
    media_type = models.CharField(max_length=10, choices=MediaType.choices)
    title = models.CharField(max_length=500)
    original_title = models.CharField(max_length=500, null=True, blank=True)
    overview = models.TextField(null=True, blank=True)
    release_date = models.DateField(null=True, blank=True)
    original_language = models.CharField(max_length=20, null=True, blank=True)
    poster_path = models.CharField(max_length=500, null=True, blank=True)
    vote_average = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
    )
    popularity = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
    )
    metadata = models.JSONField(default=dict)
    tmdb_refreshed_at = models.DateTimeField(null=True, blank=True)
    genres = models.ManyToManyField(
        Genre,
        through="ContentGenre",
        related_name="contents",
    )

    class Meta:
        db_table = "content"
        unique_together = (("tmdb_id", "media_type"),)

    def __str__(self):
        return self.title


class ContentGenre(models.Model):
    pk = models.CompositePrimaryKey("content_id", "genre_id")
    content = models.ForeignKey(Content, on_delete=models.CASCADE)
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE)

    class Meta:
        db_table = "content_genre"


class ContentEmbedding(models.Model):
    id = models.BigAutoField(primary_key=True)
    content = models.ForeignKey(
        Content,
        on_delete=models.CASCADE,
        related_name="embeddings",
    )
    embedding = VectorField(dimensions=768)
    embedding_model = models.CharField(max_length=255)
    model_version = models.CharField(max_length=100)
    source_language = models.CharField(max_length=20, default="pl-PL")
    source_text_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "content_embedding"
        unique_together = (
            ("content", "embedding_model", "model_version", "source_language"),
        )


class RunCandidate(models.Model):
    id = models.BigAutoField(primary_key=True)
    run = models.ForeignKey(
        RecommendationRun,
        on_delete=models.CASCADE,
        related_name="candidates",
    )
    content = models.ForeignKey(
        Content,
        on_delete=models.PROTECT,
        related_name="run_candidates",
    )
    source_rank = models.PositiveIntegerField(null=True, blank=True)
    relevance_score = models.DecimalField(
        max_digits=5, decimal_places=4, null=True, blank=True
    )
    critic_score = models.DecimalField(
        max_digits=5, decimal_places=4, null=True, blank=True
    )
    final_score = models.DecimalField(
        max_digits=5, decimal_places=4, null=True, blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=CandidateStatus.choices,
        default=CandidateStatus.PENDING,
    )
    final_rank = models.PositiveIntegerField(null=True, blank=True)
    decision_reason = models.TextField(null=True, blank=True)
    explanation = models.TextField(null=True, blank=True)
    metadata_snapshot = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "run_candidate"
        unique_together = (("run", "content"),)


class Interaction(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        BusinessUser,
        on_delete=models.CASCADE,
        related_name="interactions",
    )
    content = models.ForeignKey(
        Content,
        on_delete=models.PROTECT,
        related_name="interactions",
    )
    source_candidate = models.ForeignKey(
        RunCandidate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interactions",
    )
    interaction_type = models.CharField(
        max_length=30,
        choices=InteractionType.choices,
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
    )
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "interaction"


class AgentExecution(models.Model):
    id = models.BigAutoField(primary_key=True)
    run = models.ForeignKey(
        RecommendationRun,
        on_delete=models.CASCADE,
        related_name="agent_executions",
    )
    agent_type = models.CharField(max_length=100)
    sequence_no = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=AgentStatus.choices,
        default=AgentStatus.PENDING,
    )
    input_snapshot = models.JSONField(default=dict)
    output_snapshot = models.JSONField(default=dict)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "agent_execution"
        unique_together = (("run", "sequence_no"),)
