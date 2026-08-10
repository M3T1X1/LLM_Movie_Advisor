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
        if re.search(r"\b(?:gore|brutal|przemoc|straszn|dla\s+dzieci|wiekow)\w*", normalized):
            return (
                "Katalog nie zawiera pełnych oznaczeń przemocy, strasznych scen ani "
                "kategorii wiekowych, więc nie mogę tego zagwarantować. Mogę opierać "
                "się tylko na przypisanych gatunkach."
            )

        ordinal = cls._requested_ordinal(normalized)
        if ordinal is not None and ordinal < len(previous_items):
            title, description = previous_items[ordinal]
            return f"{title} — {description}"

        candidate = next(
            (
                item
                for item in candidates
                if item.title.casefold() in normalized
            ),
            candidates[0] if len(candidates) == 1 else None,
        )
        if candidate is not None:
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
                runtime = candidate.metadata.get("runtimeMinutes")
                if isinstance(runtime, (int, float)) and not isinstance(runtime, bool):
                    return f"„{candidate.title}” trwa {int(runtime)} minut."

        return (
            "Nie mam w katalogu danych potrzebnych do rzetelnej odpowiedzi na to "
            "pytanie. Mogę podać opis fabuły, gatunki, rok premiery lub ocenę, jeśli "
            "są zapisane przy tytule."
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
        warnings = ExplanationAgent._catalog_warnings(profile, current_request)
        preface = " ".join(warnings) if warnings else None
        explanations = []
        for item in selected:
            candidate = item.candidate
            facts = []
            if candidate.genres:
                facts.append(f"gatunki: {', '.join(candidate.genres)}")
            if candidate.release_date:
                facts.append(f"premiera: {candidate.release_date[:4]}")
            if candidate.vote_average is not None:
                facts.append(f"ocena katalogowa: {candidate.vote_average:.1f}/10")
            overview = ExplanationAgent._short_overview(candidate.overview)
            catalog_fit = (
                "Dane katalogowe: " + "; ".join(facts) + "."
                if facts
                else "To jedno z najbliższych dopasowań dostępnych w katalogu."
            )
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
        sentences = re.split(r"(?<=[.!?])\s+", normalized)
        value = " ".join(sentences[:2]).strip()
        if len(value) > 360:
            value = value[:357].rsplit(" ", 1)[0] + "…"
        return value

    @staticmethod
    def _catalog_warnings(
        profile: ProfilingAgentOutput,
        current_request: str,
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
            warnings.append(
                "Wybrałem pozycje oznaczone w katalogu jako „Dla dzieci” lub "
                "„Familijny”, ale katalog nie zawiera dokładnych kategorii wiekowych."
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
