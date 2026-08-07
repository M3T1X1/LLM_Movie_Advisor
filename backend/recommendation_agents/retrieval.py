import logging
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import date
from django.conf import settings
from django.db import DatabaseError
from django.db.models import Q, QuerySet
from backend.api.models import Content
from backend.embeddings import SemanticContentMatch, semantic_content_search
from backend.ollama import OllamaClient, OllamaError
from backend.recommendation_agents.profiling import ProfilingAgentOutput


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetrievalCandidate:
    content_id: int
    source_rank: int
    title: str
    media_type: str
    overview: str
    genres: tuple[str, ...]
    release_date: str | None
    vote_average: float | None
    popularity: float | None
    metadata: dict
    semantic_score: float | None

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RetrievalAgentRun:
    candidates: tuple[RetrievalCandidate, ...]
    retrieval_mode: str
    query: str

    def as_dict(self) -> dict:
        return {
            "retrieval_mode": self.retrieval_mode,
            "query": self.query,
            "candidates": [candidate.as_dict() for candidate in self.candidates],
        }


class RetrievalAgent:
    """Retrieves bounded catalog candidates using filters and pgvector."""

    def __init__(self, embedding_client: OllamaClient | None):
        self.embedding_client = embedding_client

    def run(
        self,
        current_request: str,
        profile: ProfilingAgentOutput,
        *,
        preference_hints: tuple[str, ...] = (),
    ) -> RetrievalAgentRun:
        query = self._build_query(current_request, profile)
        limit = settings.LLM_CATALOG_CANDIDATE_LIMIT
        semantic_matches: Sequence[SemanticContentMatch] = ()
        semantic_search_attempted = False

        if settings.LLM_SEMANTIC_SEARCH_ENABLED and self.embedding_client:
            semantic_search_attempted = True
            try:
                semantic_matches = semantic_content_search(
                    query,
                    list(preference_hints[:5]),
                    limit=max(limit * 10, 100),
                    client=self.embedding_client,
                )
            except (OllamaError, DatabaseError) as error:
                logger.warning("Retrieval agent semantic search failed: %s", error)

        queryset = self._constrained_queryset(profile, require_all_genres=True)
        ordered_ids, semantic_scores, contents_by_id = self._retrieve_from_queryset(
            queryset,
            profile,
            semantic_matches,
            limit,
        )

        if not ordered_ids and len(profile.genres) > 1:
            relaxed_queryset = self._constrained_queryset(
                profile,
                require_all_genres=False,
            )
            ordered_ids, semantic_scores, contents_by_id = (
                self._retrieve_from_queryset(
                    relaxed_queryset,
                    profile,
                    semantic_matches,
                    limit,
                )
            )

        if semantic_scores:
            retrieval_mode = "semantic"
        elif semantic_search_attempted:
            retrieval_mode = "keyword_fallback"
        else:
            retrieval_mode = "keyword"

        candidates = tuple(
            self._serialize_candidate(
                contents_by_id[content_id],
                source_rank=index,
                semantic_score=semantic_scores.get(content_id),
            )
            for index, content_id in enumerate(ordered_ids[:limit], start=1)
            if content_id in contents_by_id
        )
        return RetrievalAgentRun(candidates, retrieval_mode, query)

    def _retrieve_from_queryset(
        self,
        queryset: QuerySet[Content],
        profile: ProfilingAgentOutput,
        semantic_matches: Sequence[SemanticContentMatch],
        limit: int,
    ) -> tuple[list[int], dict[int, float], dict[int, Content]]:
        semantic_scores: dict[int, float] = {}
        ordered_ids: list[int] = []

        allowed_ids: set[int] = set()
        if semantic_matches:
            allowed_ids = set(
                queryset.filter(
                    pk__in=[match.content.pk for match in semantic_matches]
                ).values_list("pk", flat=True)
            )
        for match in semantic_matches:
            content_id = match.content.pk
            if (
                content_id in allowed_ids
                and content_id not in semantic_scores
                and self._runtime_matches(match.content, profile)
            ):
                ordered_ids.append(content_id)
                semantic_scores[content_id] = match.similarity

        contents_by_id: dict[int, Content] = {}
        if ordered_ids:
            contents_by_id.update(
                {
                    item.pk: item
                    for item in queryset.filter(pk__in=ordered_ids).prefetch_related(
                        "genres"
                    )
                }
            )

        if len(ordered_ids) < limit:
            terms = [
                *profile.genres,
                *profile.themes,
                *profile.reference_titles,
            ]
            keyword_filter = Q()
            for term in terms[:10]:
                keyword_filter |= (
                    Q(title__icontains=term)
                    | Q(original_title__icontains=term)
                    | Q(overview__icontains=term)
                    | Q(genres__name__icontains=term)
                )
            fallback = queryset.exclude(pk__in=ordered_ids)
            if terms:
                fallback = fallback.filter(keyword_filter)
            fallback = fallback.distinct().prefetch_related("genres").order_by(
                "-popularity", "-vote_average", "id"
            )
            batch_size = max(limit * 3, 36)
            maximum_examined = max(limit * 20, 240)
            for start in range(0, maximum_examined, batch_size):
                fallback_items = list(fallback[start : start + batch_size])
                if not fallback_items:
                    break
                for item in fallback_items:
                    if (
                        item.pk not in ordered_ids
                        and self._runtime_matches(item, profile)
                    ):
                        ordered_ids.append(item.pk)
                        contents_by_id[item.pk] = item
                        if len(ordered_ids) >= limit:
                            break
                if len(ordered_ids) >= limit:
                    break

        return ordered_ids, semantic_scores, contents_by_id

    @staticmethod
    def _build_query(current_request: str, profile: ProfilingAgentOutput) -> str:
        parts = [
            current_request.strip(),
            *profile.genres,
            *profile.themes,
            *profile.reference_titles,
        ]
        return " | ".join(dict.fromkeys(part for part in parts if part))

    @staticmethod
    def _constrained_queryset(
        profile: ProfilingAgentOutput,
        *,
        require_all_genres: bool,
    ) -> QuerySet[Content]:
        queryset = Content.objects.filter(
            Q(release_date__lte=date.today()) | Q(release_date__isnull=True)
        )
        if profile.media_types:
            queryset = queryset.filter(media_type__in=profile.media_types)
        if profile.genres:
            if require_all_genres:
                for genre in profile.genres:
                    queryset = queryset.filter(genres__name__iexact=genre)
            else:
                genre_filter = Q()
                for genre in profile.genres:
                    genre_filter |= Q(genres__name__iexact=genre)
                queryset = queryset.filter(genre_filter)
        for avoided in profile.avoid:
            excluded_genres = [avoided]
            if avoided.casefold() == "gore":
                excluded_genres.append("Horror")
            queryset = queryset.exclude(genres__name__in=excluded_genres)
        constraints = profile.constraints
        if constraints.release_year_from is not None:
            queryset = queryset.filter(
                release_date__year__gte=constraints.release_year_from
            )
        if constraints.release_year_to is not None:
            queryset = queryset.filter(
                release_date__year__lte=constraints.release_year_to
            )
        if constraints.min_vote_average is not None:
            queryset = queryset.filter(
                vote_average__gte=constraints.min_vote_average
            )
        return queryset.distinct()

    @staticmethod
    def _runtime_matches(content: Content, profile: ProfilingAgentOutput) -> bool:
        maximum = profile.constraints.max_runtime_minutes
        if maximum is None:
            return True
        runtime = (content.metadata or {}).get("runtimeMinutes")
        if runtime is None:
            return True
        return isinstance(runtime, (int, float)) and not isinstance(
            runtime, bool
        ) and runtime <= maximum

    @staticmethod
    def _serialize_candidate(
        content: Content,
        *,
        source_rank: int,
        semantic_score: float | None,
    ) -> RetrievalCandidate:
        return RetrievalCandidate(
            content_id=content.pk,
            source_rank=source_rank,
            title=content.title,
            media_type=content.media_type,
            overview=(content.overview or "")[: settings.LLM_CATALOG_OVERVIEW_MAX_LENGTH],
            genres=tuple(genre.name for genre in content.genres.all()),
            release_date=content.release_date.isoformat() if content.release_date else None,
            vote_average=float(content.vote_average) if content.vote_average is not None else None,
            popularity=float(content.popularity) if content.popularity is not None else None,
            metadata=content.metadata or {},
            semantic_score=semantic_score,
        )
