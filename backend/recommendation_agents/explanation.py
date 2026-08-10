import re
from dataclasses import dataclass

from backend.ollama import OllamaClient
from backend.recommendation_agents.profiling import ProfilingAgentOutput
from backend.recommendation_agents.ranking import RankedCandidate
from backend.recommendation_agents.retrieval import RetrievalCandidate


class ExplanationAgentError(Exception):
    pass


@dataclass(frozen=True)
class CandidateExplanation:
    content_id: int
    explanation: str


@dataclass(frozen=True)
class ExplanationAgentRun:
    message: str
    explanations: tuple[CandidateExplanation, ...]
    model: str
    prompt_tokens: int | None
    generated_tokens: int | None
    source: str = "model"
    fallback_reason: str | None = None

    def as_dict(self) -> dict:
        return {
            "message": self.message,
            "explanations": [
                {"content_id": item.content_id, "explanation": item.explanation}
                for item in self.explanations
            ],
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "generated_tokens": self.generated_tokens,
            "source": self.source,
            "fallback_reason": self.fallback_reason,
        }


class ExplanationAgent:
    def __init__(self, client: OllamaClient):
        self.client = client

    def run(
        self,
        current_request: str,
        profile: ProfilingAgentOutput,
        selected: tuple[RankedCandidate, ...],
    ) -> ExplanationAgentRun:
        if not selected:
            return ExplanationAgentRun(
                self._no_candidates_message(profile),
                (), self.client.model, None, None, "catalog", "no_candidates",
            )
        # Recommendation descriptions are intentionally composed from catalog
        # fields. Free-form generation here used to invent endings, characters
        # and content-safety guarantees that were absent from the data.
        message, explanations = self._fallback_from_catalog(
            profile,
            selected,
            current_request=current_request,
        )
        return ExplanationAgentRun(
            message,
            explanations,
            self.client.model,
            None,
            None,
            "catalog",
            None,
        )

    def answer_content_question(
        self,
        current_request: str,
        candidates: tuple[RetrievalCandidate, ...],
        conversation_history: tuple[dict[str, str], ...] = (),
    ) -> ExplanationAgentRun:
        message = self._grounded_content_answer(
            current_request,
            candidates,
            conversation_history,
        )
        return ExplanationAgentRun(
            message,
            (),
            self.client.model,
            None,
            None,
            "catalog",
            None,
        )

    @classmethod
    def _grounded_content_answer(
        cls,
        current_request: str,
        candidates: tuple[RetrievalCandidate, ...],
        conversation_history: tuple[dict[str, str], ...],
    ) -> str:
        normalized = current_request.casefold()
        previous_items = cls._previous_recommendation_items(conversation_history)

        if re.search(r"\b(?:happy\s+end|szczęśliw\w*\s+zakończ|zakończen)\w*", normalized):
            return (
                "Nie mogę rzetelnie potwierdzić rodzaju zakończenia tych pozycji: "
                "katalog nie przechowuje takiej informacji. Nie będę zgadywać ani "
                "zdradzać zakończeń."
            )
        ordinal = cls._requested_ordinal(normalized)
        candidate = next(
            (
                item
                for item in candidates
                if item.title.casefold() in normalized
            ),
            candidates[0] if len(candidates) == 1 else None,
        )
        if candidate is not None:
            metadata = candidate.metadata
            if re.search(r"\b(?:reżyser|reżyserow)\w*", normalized):
                directors = cls._metadata_names(metadata.get("directors"))
                if directors:
                    return f"Reżyseria „{candidate.title}”: {', '.join(directors)}."
            if re.search(r"\b(?:aktor|obsad|gra\s+w|występuj)\w*", normalized):
                cast = cls._metadata_names(metadata.get("cast"))
                if cast:
                    return f"Główna obsada „{candidate.title}”: {', '.join(cast[:6])}."
            if re.search(r"\bsezon\w*", normalized):
                seasons = metadata.get("seasonCount")
                if isinstance(seasons, int) and not isinstance(seasons, bool):
                    return f"„{candidate.title}” ma {seasons} sezonów w danych katalogowych."
            if re.search(r"\bodcink\w*", normalized):
                episodes = metadata.get("episodeCount")
                episode_runtime = metadata.get("episodeRuntimeMinutes")
                facts = []
                if isinstance(episodes, int) and not isinstance(episodes, bool):
                    facts.append(f"{episodes} odcinków")
                if isinstance(episode_runtime, (int, float)) and not isinstance(
                    episode_runtime,
                    bool,
                ):
                    facts.append(f"około {int(episode_runtime)} minut na odcinek")
                if facts:
                    return f"„{candidate.title}”: {', '.join(facts)}."
            if re.search(
                r"\b(?:kategoria\s+wiekow|rating\s+wiekow|od\s+ilu\s+lat|dla\s+dzieci)\w*",
                normalized,
            ):
                age_rating = metadata.get("ageRating")
                if isinstance(age_rating, str) and age_rating.strip():
                    return (
                        f"Kategoria wiekowa „{candidate.title}” w katalogu: "
                        f"{age_rating.strip()}."
                    )
            if re.search(r"\b(?:o\s+czym|fabuł|opowiad|opis)\w*", normalized):
                if candidate.overview.strip():
                    return f"{candidate.title} — {cls._short_overview(candidate.overview)}"
            if re.search(r"\b(?:ocen|rating)\w*", normalized):
                if candidate.vote_average is not None:
                    return f"Ocena katalogowa „{candidate.title}” to {candidate.vote_average:.1f}/10."
            if re.search(r"\b(?:premier|rok\w*|kiedy)\w*", normalized):
                if candidate.release_date:
                    return f"Premiera „{candidate.title}”: {candidate.release_date}."
            if re.search(r"\b(?:trwa|dług\w*|minut)\w*", normalized):
                runtime_key = (
                    "runtimeMinutes"
                    if candidate.media_type == "movie"
                    else "episodeRuntimeMinutes"
                )
                runtime = candidate.metadata.get(runtime_key)
                if isinstance(runtime, (int, float)) and not isinstance(runtime, bool):
                    subject = (
                        f"„{candidate.title}”"
                        if candidate.media_type == "movie"
                        else f"Odcinek „{candidate.title}”"
                    )
                    return f"{subject} trwa około {int(runtime)} minut."

        if ordinal is not None and ordinal < len(previous_items):
            title, description = previous_items[ordinal]
            if re.search(r"\b(?:o\s+czym|fabuł|opowiad|opis)\w*", normalized):
                return f"{title} — {description}"

        if re.search(r"\b(?:gore|brutal|przemoc|straszn|dla\s+dzieci|wiekow)\w*", normalized):
            return (
                "Katalog nie zawiera pełnych oznaczeń przemocy ani strasznych scen. "
                "Jeśli przy tytule nie ma kategorii wiekowej, nie mogę zagwarantować "
                "jego przydatności dla konkretnego wieku."
            )

        return (
            "Nie mam w katalogu danych potrzebnych do rzetelnej odpowiedzi na to "
            "pytanie. Mogę podać opis, rok, ocenę, czas, reżyserię, obsadę, sezony "
            "lub kategorię wiekową, jeśli są zapisane przy tytule."
        )

    @staticmethod
    def _metadata_names(value: object) -> tuple[str, ...]:
        if not isinstance(value, list):
            return ()
        return tuple(
            item.strip()
            for item in value
            if isinstance(item, str) and item.strip()
        )

    @staticmethod
    def _previous_recommendation_items(
        conversation_history: tuple[dict[str, str], ...],
    ) -> tuple[tuple[str, str], ...]:
        for message in reversed(conversation_history):
            if message.get("role") != "assistant":
                continue
            matches = re.findall(
                r"(?m)^\s*\d+\.\s+(.+?)\s+[—-]\s+(.+?)\s*$",
                str(message.get("content", "")),
            )
            if matches:
                return tuple(
                    (title.strip(), description.strip())
                    for title, description in matches
                )
        return ()

    @staticmethod
    def _requested_ordinal(normalized: str) -> int | None:
        patterns = (
            (r"\b(?:pierwsz\w*|1\.)", 0),
            (r"\b(?:drug\w*|2\.)", 1),
            (r"\b(?:trzeci\w*|3\.)", 2),
        )
        return next(
            (value for pattern, value in patterns if re.search(pattern, normalized)),
            None,
        )

    @staticmethod
    def _fallback_from_catalog(
        profile: ProfilingAgentOutput,
        selected: tuple[RankedCandidate, ...],
        *,
        current_request: str = "",
    ) -> tuple[str, tuple[CandidateExplanation, ...]]:
        warnings = ExplanationAgent._catalog_warnings(
            profile,
            current_request,
            selected,
        )
        preface = " ".join(warnings) if warnings else None
        explanations = []
        for item in selected:
            candidate = item.candidate
            overview = ExplanationAgent._short_overview(candidate.overview)
            catalog_fit = ExplanationAgent._fit_summary(profile, candidate)
            explanation = f"{overview} {catalog_fit}" if overview else catalog_fit
            explanations.append(
                CandidateExplanation(candidate.content_id, explanation)
            )
        explanation_values = tuple(explanations)
        return (
            ExplanationAgent._descriptive_chat_message(
                selected,
                explanation_values,
                preface=preface,
            ),
            explanation_values,
        )

    @staticmethod
    def _short_overview(overview: str) -> str:
        normalized = re.sub(r"\s+", " ", overview).strip()
        if not normalized:
            return ""
        value = re.split(r"(?<=[.!?])\s+", normalized)[0].strip()
        if len(value) > 190:
            value = value[:187].rsplit(" ", 1)[0] + "…"
        return value

    @staticmethod
    def _fit_summary(
        profile: ProfilingAgentOutput,
        candidate: RetrievalCandidate,
    ) -> str:
        candidate_genres = {genre.casefold(): genre for genre in candidate.genres}
        requested = list(profile.genres)
        if "Dla dzieci" in requested:
            requested.extend(("Familijny", "Animacja"))
        if "lekki klimat" in profile.themes and not requested:
            requested.extend(("Komedia", "Familijny", "Romans", "Reality show"))
        matches = [
            candidate_genres[genre.casefold()]
            for genre in requested
            if genre.casefold() in candidate_genres
        ]
        facts = []
        if matches:
            facts.append("pasuje: " + ", ".join(dict.fromkeys(matches[:2])))
        if candidate.release_date:
            facts.append(candidate.release_date[:4])
        if candidate.vote_average is not None:
            facts.append(f"{candidate.vote_average:.1f}/10")
        runtime_key = (
            "runtimeMinutes" if candidate.media_type == "movie"
            else "episodeRuntimeMinutes"
        )
        runtime = candidate.metadata.get(runtime_key)
        if isinstance(runtime, (int, float)) and not isinstance(runtime, bool):
            suffix = "min" if candidate.media_type == "movie" else "min/odc"
            facts.append(f"{int(runtime)} {suffix}")
        if "Dla dzieci" in profile.genres:
            age_rating = candidate.metadata.get("ageRating")
            if isinstance(age_rating, str) and age_rating.strip():
                facts.append(f"wiek: {age_rating.strip()}")
        if not facts:
            return "Najbliższe dostępne dopasowanie katalogowe."
        return " • ".join(facts).capitalize() + "."

    @staticmethod
    def _catalog_warnings(
        profile: ProfilingAgentOutput,
        current_request: str,
        selected: tuple[RankedCandidate, ...],
    ) -> tuple[str, ...]:
        warnings = []
        normalized_request = current_request.casefold()
        maximum = profile.constraints.max_runtime_minutes
        if maximum is not None:
            warnings.append(
                f"Limit {maximum} minut został zastosowany wyłącznie do pozycji "
                "z potwierdzonym czasem trwania w katalogu."
            )
        if "szczęśliwe zakończenie" in profile.themes:
            warnings.append(
                "Uwaga: katalog nie oznacza rodzaju zakończenia, więc happy end nie jest potwierdzony."
            )
        if re.search(
            r"\b(?:gore|brutal|przemoc|straszn|graficzn)\w*",
            normalized_request,
        ):
            warnings.append(
                "Uwaga: katalog nie ma pełnych oznaczeń brutalności ani gore; nie mogę zagwarantować ich braku."
            )
        if "Dla dzieci" in profile.genres:
            missing_age_ratings = any(
                not isinstance(item.candidate.metadata.get("ageRating"), str)
                or not item.candidate.metadata.get("ageRating", "").strip()
                for item in selected
            )
            if missing_age_ratings:
                warnings.append(
                    "Wybrałem pozycje dziecięce lub familijne, ale nie wszystkie "
                    "mają w katalogu kategorię wiekową."
                )
        return tuple(warnings)

    @staticmethod
    def _no_candidates_message(profile: ProfilingAgentOutput) -> str:
        maximum = profile.constraints.max_runtime_minutes
        if maximum is not None:
            return (
                f"Nie znalazłem w katalogu pozycji z potwierdzonym czasem trwania "
                f"do {maximum} minut, które spełniają pozostałe warunki."
            )
        if "Dla dzieci" in profile.genres:
            return (
                "Nie znalazłem pozycji oznaczonych w katalogu jako „Dla dzieci”, "
                "które spełniają pozostałe warunki."
            )
        if "krótkie odcinki" in profile.themes:
            return (
                "Nie znalazłem seriali z potwierdzonym czasem odcinka do 35 minut, "
                "które spełniają pozostałe warunki."
            )
        return "Nie znalazłem w katalogu pozycji spełniających tę prośbę."

    @staticmethod
    def _descriptive_chat_message(
        selected: tuple[RankedCandidate, ...],
        explanations: tuple[CandidateExplanation, ...],
        *,
        preface: str | None = None,
    ) -> str:
        explanations_by_id = {
            item.content_id: item.explanation for item in explanations
        }
        lines = [preface or "Mam dla Ciebie te propozycje:"]
        lines.extend(
            f"{index}. {item.candidate.title} — "
            f"{explanations_by_id[item.candidate.content_id]}"
            for index, item in enumerate(selected, start=1)
        )
        return "\n".join(lines)
