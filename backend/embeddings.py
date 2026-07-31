import hashlib
import unicodedata
from dataclasses import dataclass
from datetime import date

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from pgvector.django import CosineDistance

from backend.api.models import Content, ContentEmbedding
from backend.ollama import OllamaClient, get_ollama_client
from backend.redis import invalidate_catalog_search_cache


@dataclass(frozen=True)
class EmbeddingSyncResult:
    examined: int
    generated: int
    created: int
    updated: int
    skipped: int


@dataclass(frozen=True)
class SemanticContentMatch:
    content: Content
    similarity: float


def normalize_embedding_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return " ".join(normalized.split())


def build_content_embedding_text(content: Content) -> str:
    genres = ", ".join(sorted(genre.name for genre in content.genres.all()))
    media_type = "film" if content.media_type == "movie" else "serial"
    fields = [
        f"Tytuł: {content.title}",
        f"Typ: {media_type}",
    ]
    if content.original_title and content.original_title != content.title:
        fields.append(f"Tytuł oryginalny: {content.original_title}")
    if genres:
        fields.append(f"Gatunki: {genres}")
    if content.release_date:
        fields.append(f"Rok premiery: {content.release_date.year}")
    if content.original_language:
        fields.append(f"Język oryginalny: {content.original_language}")
    if content.overview:
        fields.append(f"Opis: {content.overview}")
    return "search_document: " + normalize_embedding_text(". ".join(fields))


def build_query_embedding_text(prompt: str, preference_hints: list[str]) -> str:
    fields = [normalize_embedding_text(prompt)]
    normalized_hints: list[str] = []
    for value in preference_hints:
        normalized_value = normalize_embedding_text(value)
        if normalized_value:
            normalized_hints.append(normalized_value)
    if normalized_hints:
        fields.append("Preferencje: " + ", ".join(normalized_hints[:5]))
    return "search_query: " + ". ".join(fields)


def embedding_source_hash(source_text: str) -> str:
    return hashlib.sha256(source_text.encode("utf-8")).hexdigest()


def sync_content_embeddings(
    *,
    content_ids: list[int] | None = None,
    batch_size: int | None = None,
    force: bool = False,
    limit: int | None = None,
    client: OllamaClient | None = None,
) -> EmbeddingSyncResult:
    resolved_batch_size = batch_size or settings.LLM_EMBEDDING_BATCH_SIZE
    if resolved_batch_size < 1:
        raise ValueError("Embedding batch size must be greater than zero.")
    if limit is not None and limit < 1:
        raise ValueError("Embedding limit must be greater than zero.")

    queryset = Content.objects.prefetch_related("genres").order_by("id")
    if content_ids is not None:
        if not content_ids:
            return EmbeddingSyncResult(0, 0, 0, 0, 0)
        queryset = queryset.filter(pk__in=list(dict.fromkeys(content_ids)))
    if limit is not None:
        queryset = queryset[:limit]
    contents = list(queryset)

    existing_hashes = dict(
        ContentEmbedding.objects.filter(
            content_id__in=[content.pk for content in contents],
            embedding_model=settings.OLLAMA_EMBEDDING_MODEL,
            model_version=settings.LLM_EMBEDDING_MODEL_VERSION,
            source_language=settings.LLM_EMBEDDING_SOURCE_LANGUAGE,
        ).values_list("content_id", "source_text_hash")
    )
    pending: list[tuple[Content, str, str]] = []
    for content in contents:
        source_text = build_content_embedding_text(content)
        source_hash = embedding_source_hash(source_text)
        if not force and existing_hashes.get(content.pk) == source_hash:
            continue
        pending.append((content, source_text, source_hash))

    embedding_client = client or get_ollama_client()
    created = 0
    updated = 0
    for start in range(0, len(pending), resolved_batch_size):
        batch = pending[start : start + resolved_batch_size]
        response = embedding_client.embed([item[1] for item in batch])
        now = timezone.now()
        with transaction.atomic():
            for (content, _, source_hash), embedding in zip(
                batch,
                response.embeddings,
                strict=True,
            ):
                _, was_created = ContentEmbedding.objects.update_or_create(
                    content=content,
                    embedding_model=settings.OLLAMA_EMBEDDING_MODEL,
                    model_version=settings.LLM_EMBEDDING_MODEL_VERSION,
                    source_language=settings.LLM_EMBEDDING_SOURCE_LANGUAGE,
                    defaults={
                        "embedding": list(embedding),
                        "source_text_hash": source_hash,
                        "updated_at": now,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

    generated = len(pending)
    if generated:
        invalidate_catalog_search_cache()
    return EmbeddingSyncResult(
        examined=len(contents),
        generated=generated,
        created=created,
        updated=updated,
        skipped=len(contents) - generated,
    )


def semantic_content_search(
    prompt: str,
    preference_hints: list[str],
    *,
    limit: int,
    client: OllamaClient,
) -> list[SemanticContentMatch]:
    if limit < 1:
        return []
    query_text = build_query_embedding_text(prompt, preference_hints)
    query_embedding = list(client.embed([query_text]).embeddings[0])
    maximum_distance = 1.0 - settings.LLM_SEMANTIC_MIN_SIMILARITY
    embeddings = list(
        ContentEmbedding.objects.filter(
            Q(content__release_date__lte=date.today())
            | Q(content__release_date__isnull=True),
            embedding_model=settings.OLLAMA_EMBEDDING_MODEL,
            model_version=settings.LLM_EMBEDDING_MODEL_VERSION,
            source_language=settings.LLM_EMBEDDING_SOURCE_LANGUAGE,
        )
        .select_related("content")
        .prefetch_related("content__genres")
        .annotate(distance=CosineDistance("embedding", query_embedding))
        .filter(distance__lte=maximum_distance)
        .order_by("distance", "content_id")[:limit]
    )
    return [
        SemanticContentMatch(
            content=item.content,
            similarity=max(0.0, min(1.0, 1.0 - float(item.distance))),
        )
        for item in embeddings
    ]
