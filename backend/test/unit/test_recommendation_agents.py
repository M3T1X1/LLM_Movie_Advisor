import json
from unittest.mock import MagicMock, call, patch

from django.test import SimpleTestCase, override_settings

from backend.ollama import OllamaChatResponse
from backend.recommendation_agents.explanation import (
    ExplanationAgent,
    ExplanationAgentRun,
)
from backend.recommendation_agents.graph import build_recommendation_graph
from backend.recommendation_agents.profiling import (
    ProfilingAgentInput,
    ProfilingAgentOutput,
    ProfilingAgentRun,
    ProfilingConstraints,
)
from backend.recommendation_agents.ranking import (
    RankedCandidate,
    RankingAgent,
    RankingAgentError,
    RankingAgentRun,
)
from backend.recommendation_agents.retrieval import (
    RetrievalAgent,
    RetrievalAgentRun,
    RetrievalCandidate,
)


def profile(**changes):
    values = {
        "intent": "recommendation",
        "mood": "mroczny",
        "media_types": ("movie",),
        "genres": ("Thriller",),
        "themes": ("tajemnica",),
        "avoid": (),
        "reference_titles": (),
        "constraints": ProfilingConstraints(None, None, None, None),
        "needs_clarification": False,
        "clarification_question": None,
        "confidence": 0.9,
        "evidence": ("mroczny thriller",),
    }
    values.update(changes)
    return ProfilingAgentOutput(**values)


def candidate(content_id, source_rank=1, title=None):
    return RetrievalCandidate(
        content_id=content_id,
        source_rank=source_rank,
        title=title or f"Film {content_id}",
        media_type="movie",
        overview="Mroczna tajemnica.",
        genres=("Thriller",),
        release_date="2020-01-01",
        vote_average=8.0,
        popularity=100.0,
        metadata={"runtimeMinutes": 110},
        semantic_score=0.8,
    )


def response(payload):
    return OllamaChatResponse(
        content=json.dumps(payload),
        model="llama3.1:8b",
        done_reason="stop",
        total_duration_ns=100,
        prompt_eval_count=20,
        eval_count=10,
    )


class RetrievalAgentTests(SimpleTestCase):
    def test_builds_query_and_applies_runtime_constraint(self):
        output = profile(
            themes=("izolacja",),
            reference_titles=("The Thing",),
            constraints=ProfilingConstraints(100, None, None, None),
        )
        content = MagicMock(metadata={"runtimeMinutes": 120})

        query = RetrievalAgent._build_query("Mroczny film", output)

        self.assertEqual(query, "Mroczny film | Thriller | izolacja | The Thing")
        self.assertFalse(RetrievalAgent._runtime_matches(content, output))

    @patch("backend.recommendation_agents.retrieval.Content.objects.filter")
    def test_gore_avoidance_does_not_exclude_the_horror_genre(self, objects_filter):
        queryset = MagicMock()
        objects_filter.return_value = queryset

        RetrievalAgent._constrained_queryset(
            profile(genres=(), avoid=("Gore",)),
            require_all_genres=True,
        )

        queryset.exclude.assert_not_called()

    def test_missing_runtime_cannot_satisfy_a_hard_limit(self):
        output = profile(
            constraints=ProfilingConstraints(100, None, None, None),
        )
        content = MagicMock(metadata={})

        self.assertFalse(RetrievalAgent._runtime_matches(content, output))

    def test_short_episode_theme_requires_verified_episode_runtime(self):
        output = profile(
            media_types=("tv",),
            themes=("krótkie odcinki",),
        )
        short = MagicMock(
            media_type="tv",
            metadata={"episodeRuntimeMinutes": 24},
        )
        unknown = MagicMock(media_type="tv", metadata={})

        self.assertTrue(
            RetrievalAgent._candidate_matches_constraints(short, output)
        )
        self.assertFalse(
            RetrievalAgent._candidate_matches_constraints(unknown, output)
        )

    @override_settings(
        LLM_SEMANTIC_SEARCH_ENABLED=False,
        LLM_CATALOG_CANDIDATE_LIMIT=12,
    )
    def test_does_not_backfill_two_specific_matches_with_popular_titles(self):
        output = profile(genres=(), themes=("izolacja",))
        queryset = MagicMock()
        keyword_queryset = queryset.exclude.return_value.filter.return_value
        ordered_queryset = (
            keyword_queryset.distinct.return_value
            .prefetch_related.return_value
            .order_by.return_value
        )
        ordered_queryset.__getitem__.return_value = [
            MagicMock(pk=1),
            MagicMock(pk=2),
        ]
        agent = RetrievalAgent(None)

        with (
            patch.object(
                RetrievalAgent,
                "_constrained_queryset",
                return_value=queryset,
            ),
            patch.object(
                RetrievalAgent,
                "_serialize_candidate",
                side_effect=(candidate(1), candidate(2)),
            ),
        ):
            run = agent.run("Film o izolacji", output)

        self.assertEqual(
            [item.content_id for item in run.candidates],
            [1, 2],
        )
        queryset.exclude.assert_called_once()

    @override_settings(
        LLM_SEMANTIC_SEARCH_ENABLED=False,
        LLM_CATALOG_CANDIDATE_LIMIT=12,
    )
    def test_keeps_one_strict_genre_intersection_without_relaxing_to_or(self):
        output = profile(genres=("Horror", "Science Fiction"), themes=())
        strict_queryset = MagicMock()
        strict_content = MagicMock(pk=1)
        agent = RetrievalAgent(None)

        with (
            patch.object(
                RetrievalAgent,
                "_constrained_queryset",
                return_value=strict_queryset,
            ) as constrained_queryset,
            patch.object(
                RetrievalAgent,
                "_retrieve_from_queryset",
                return_value=([1], {}, {1: strict_content}),
            ) as retrieve,
            patch.object(
                RetrievalAgent,
                "_serialize_candidate",
                return_value=candidate(1),
            ),
        ):
            run = agent.run("Horror science fiction", output)

        self.assertEqual([item.content_id for item in run.candidates], [1])
        constrained_queryset.assert_called_once_with(
            output,
            require_all_genres=True,
        )
        retrieve.assert_called_once_with(strict_queryset, output, (), 12)

    @override_settings(
        LLM_SEMANTIC_SEARCH_ENABLED=False,
        LLM_CATALOG_CANDIDATE_LIMIT=12,
    )
    def test_relaxes_multiple_genres_to_or_only_when_intersection_is_empty(self):
        output = profile(genres=("Horror", "Science Fiction"), themes=())
        strict_queryset = MagicMock()
        relaxed_queryset = MagicMock()
        relaxed_contents = {1: MagicMock(pk=1), 2: MagicMock(pk=2)}
        agent = RetrievalAgent(None)

        with (
            patch.object(
                RetrievalAgent,
                "_constrained_queryset",
                side_effect=(strict_queryset, relaxed_queryset),
            ) as constrained_queryset,
            patch.object(
                RetrievalAgent,
                "_retrieve_from_queryset",
                side_effect=(([], {}, {}), ([1, 2], {}, relaxed_contents)),
            ) as retrieve,
            patch.object(
                RetrievalAgent,
                "_serialize_candidate",
                side_effect=(candidate(1), candidate(2)),
            ),
        ):
            run = agent.run("Horror science fiction", output)

        self.assertEqual(
            [item.content_id for item in run.candidates],
            [1, 2],
        )
        self.assertEqual(
            constrained_queryset.call_args_list,
            [
                call(output, require_all_genres=True),
                call(output, require_all_genres=False),
            ],
        )
        self.assertEqual(
            retrieve.call_args_list,
            [
                call(strict_queryset, output, (), 12),
                call(relaxed_queryset, output, (), 12),
            ],
        )


class RankingAgentTests(SimpleTestCase):
    def setUp(self):
        self.client = MagicMock(model="llama3.1:8b")
        self.agent = RankingAgent(self.client)
        self.candidates = (candidate(1, 1), candidate(2, 2))

    def test_scores_candidates_with_validated_model_output(self):
        self.client.chat.return_value = response(
            {
                "scores": [
                    {"content_id": 1, "relevance_score": 0.5, "critic_score": 0.8, "decision_reason": "Dobre dane."},
                    {"content_id": 2, "relevance_score": 0.9, "critic_score": 0.9, "decision_reason": "Najlepsze dopasowanie."},
                ]
            }
        )

        run = self.agent.run("Mroczny thriller", profile(), self.candidates)

        self.assertEqual([item.candidate.content_id for item in run.candidates], [2, 1])
        self.assertEqual([item.final_rank for item in run.selected], [1, 2])
        self.assertEqual(run.source, "model")
        self.client.chat.assert_called_once()

    def test_falls_back_when_candidate_score_is_missing(self):
        self.client.chat.return_value = response(
            {"scores": [{"content_id": 1, "relevance_score": 0.8, "critic_score": 0.8, "decision_reason": "OK"}]}
        )
        run = self.agent.run("Thriller", profile(), self.candidates)

        self.assertEqual(len(run.candidates), 2)
        self.assertEqual(len(run.selected), 2)
        self.assertEqual(run.source, "hybrid")

    def test_accepts_safe_numeric_strings_and_ignores_extra_model_fields(self):
        self.client.chat.return_value = response(
            {
                "scores": [
                    {
                        "content_id": "1",
                        "relevance_score": "0.8",
                        "critic_score": "0.7",
                        "decision_reason": "Pasuje.",
                        "unused": "ignored",
                    }
                ],
                "unused": True,
            }
        )

        run = self.agent.run("Thriller", profile(), self.candidates)

        first = next(item for item in run.candidates if item.candidate.content_id == 1)
        self.assertEqual(first.relevance_score, 0.8)
        self.assertEqual(run.source, "hybrid")

    def test_ignores_malformed_individual_model_score(self):
        self.client.chat.return_value = response(
            {
                "scores": [
                    {"content_id": 1},
                    {
                        "content_id": 2,
                        "relevance_score": 0.8,
                        "critic_score": 0.7,
                        "decision_reason": "Pasuje.",
                    },
                ]
            }
        )

        run = self.agent.run("Thriller", profile(), self.candidates)

        self.assertEqual(len(run.candidates), 2)
        self.assertEqual(run.source, "hybrid")

    def test_good_request_rejects_low_rated_candidate(self):
        low = RetrievalCandidate(
            **{**candidate(1).__dict__, "vote_average": 4.8}
        )
        good = RetrievalCandidate(
            **{**candidate(2).__dict__, "vote_average": 7.2}
        )
        self.client.chat.return_value = response(
            {
                "scores": [
                    {"content_id": 1, "relevance_score": 0.9, "critic_score": 0.9, "decision_reason": "Pasuje."},
                    {"content_id": 2, "relevance_score": 0.8, "critic_score": 0.8, "decision_reason": "Pasuje."},
                ]
            }
        )

        run = self.agent.run("Poleć dobry horror", profile(), (low, good))

        self.assertEqual(
            [item.candidate.content_id for item in run.selected],
            [2],
        )

    def test_good_mood_does_not_create_quality_threshold(self):
        self.assertIsNone(
            RankingAgent._requested_quality_minimum(
                "Mam dobry nastrój, poleć komedię.",
                profile(),
            )
        )

    def test_light_request_does_not_turn_explicit_genre_into_hard_exclusion(self):
        light_profile = profile(
            genres=("Komedia",),
            themes=("lekki klimat", "humor"),
        )
        heavy = candidate(1)
        heavy = RetrievalCandidate(
            **{**heavy.__dict__, "genres": ("Komedia", "Thriller")}
        )
        light = candidate(2)
        light = RetrievalCandidate(
            **{**light.__dict__, "genres": ("Komedia", "Familijny")}
        )
        self.client.chat.return_value = response(
            {
                "scores": [
                    {"content_id": 1, "relevance_score": 1.0, "critic_score": 1.0, "decision_reason": "Model wybrał thriller."},
                    {"content_id": 2, "relevance_score": 0.7, "critic_score": 0.7, "decision_reason": "Lekka komedia."},
                ]
            }
        )

        run = self.agent.run("Lekka komedia", light_profile, (heavy, light))

        self.assertEqual(len(run.selected), 2)
        self.assertGreater(run.candidates[0].relevance_score, 0)

    def test_model_reason_cannot_override_catalog_eligibility(self):
        self.client.chat.return_value = response(
            {
                "scores": [
                    {
                        "content_id": 1,
                        "relevance_score": 0.95,
                        "critic_score": 0.9,
                        "decision_reason": "Film nie pasuje do prośby użytkownika.",
                    },
                    {
                        "content_id": 2,
                        "relevance_score": 0.8,
                        "critic_score": 0.8,
                        "decision_reason": "Dobre dopasowanie.",
                    },
                ]
            }
        )

        run = self.agent.run("Lekki film", profile(), self.candidates)

        selected = next(item for item in run.candidates if item.candidate.content_id == 1)
        self.assertEqual(selected.status, "selected")
        self.assertEqual(selected.relevance_score, 0.95)


class ExplanationAgentTests(SimpleTestCase):
    def setUp(self):
        self.client = MagicMock(model="llama3.1:8b")
        base = candidate(1)
        self.selected = (
            RankedCandidate(base, 0.9, 0.8, 0.865, "selected", 1, "Pasuje."),
        )
        self.agent = ExplanationAgent(self.client)

    def test_explains_each_selected_candidate(self):
        run = self.agent.run("Mroczny thriller", profile(), self.selected)

        self.assertIn("1. Film 1 — Mroczna tajemnica.", run.message)
        self.assertIn("Pasuje: thriller", run.message)
        self.assertEqual(run.explanations[0].content_id, 1)
        self.assertIn("8.0/10", run.explanations[0].explanation)
        self.assertEqual(run.model, "llama3.1:8b")
        self.assertEqual(run.source, "catalog")
        self.client.chat.assert_not_called()

    def test_catalog_description_is_short(self):
        long_candidate = RetrievalCandidate(
            **{
                **candidate(1).__dict__,
                "overview": "Bardzo długi opis " * 40,
            }
        )
        selected = (
            RankedCandidate(
                long_candidate, 0.9, 0.8, 0.865, "selected", 1, "Pasuje."
            ),
        )

        run = self.agent.run("Thriller", profile(), selected)

        self.assertLess(len(run.explanations[0].explanation), 260)

    def test_chat_message_describes_every_selected_title(self):
        second = RankedCandidate(
            candidate(2, source_rank=2, title="Drugi film"),
            relevance_score=0.8,
            critic_score=0.7,
            final_score=0.765,
            status="selected",
            final_rank=2,
            decision_reason="Pasuje.",
        )
        run = self.agent.run(
            "Mroczne filmy",
            profile(),
            (*self.selected, second),
        )

        self.assertIn("1. Film 1 — Mroczna tajemnica.", run.message)
        self.assertIn("2. Drugi film — Mroczna tajemnica.", run.message)

    def test_falls_back_for_explanation_of_unknown_candidate(self):
        self.client.chat.return_value = response(
            {"message": "Wynik.", "explanations": [{"content_id": 999, "explanation": "Nieznany film."}]}
        )
        run = self.agent.run("Thriller", profile(), self.selected)

        self.assertIn("Film 1", run.message)
        self.assertEqual(run.explanations[0].content_id, 1)

    def test_catalog_description_does_not_call_model(self):
        run = self.agent.run("Thriller", profile(), self.selected)

        self.assertIn("Film 1", run.message)
        self.assertEqual(run.explanations[0].content_id, 1)
        self.assertEqual(run.source, "catalog")
        self.client.chat.assert_not_called()

    def test_falls_back_for_duplicate_candidate_explanation(self):
        self.client.chat.return_value = response(
            {
                "message": "Wynik.",
                "explanations": [
                    {"content_id": 1, "explanation": "Pierwszy opis."},
                    {"content_id": 1, "explanation": "Drugi opis."},
                ],
            }
        )

        run = self.agent.run("Thriller", profile(), self.selected)

        self.assertIn("Film 1", run.message)
        self.assertEqual(len(run.explanations), 1)

    def test_falls_back_for_protected_model_output(self):
        self.client.chat.return_value = response(
            {
                "message": "Oto dane user_profile.",
                "explanations": [
                    {"content_id": 1, "explanation": "Opis filmu."},
                ],
            }
        )

        run = self.agent.run("Thriller", profile(), self.selected)

        self.assertNotIn("user_profile", run.message)
        self.assertIn("Film 1", run.message)

    def test_does_not_call_model_when_no_candidate_was_selected(self):
        run = self.agent.run("Thriller", profile(), ())

        self.assertIn("Nie znalazłem", run.message)
        self.assertEqual(run.explanations, ())
        self.client.chat.assert_not_called()

    def test_discloses_missing_runtime_instead_of_claiming_constraint_match(self):
        without_runtime = candidate(1)
        without_runtime = RetrievalCandidate(
            **{**without_runtime.__dict__, "metadata": {}}
        )
        selected = (
            RankedCandidate(
                without_runtime, 0.9, 0.8, 0.865, "selected", 1, "Pasuje."
            ),
        )

        run = self.agent.run(
            "Film do 100 minut",
            profile(constraints=ProfilingConstraints(100, None, None, None)),
            selected,
        )

        self.assertIn("Limit 100 minut", run.message)
        self.client.chat.assert_not_called()

    def test_answers_content_question_from_catalog_context(self):
        run = self.agent.answer_content_question(
            "O czym jest ten film?",
            (candidate(1, title="Zagadka"),),
            ({"role": "assistant", "content": "Poleciłem tytuł Zagadka."},),
        )

        self.assertEqual(run.message, "Zagadka — Mroczna tajemnica.")
        self.assertEqual(run.explanations, ())
        self.client.chat.assert_not_called()

    def test_content_question_is_honest_when_catalog_has_no_answer(self):
        run = self.agent.answer_content_question("Kto reżyserował ten film?", ())

        self.assertIn("danych potrzebnych", run.message)
        self.assertEqual(run.source, "catalog")

    def test_answers_question_about_first_previous_recommendation(self):
        history = (
            {
                "role": "assistant",
                "content": (
                    "Mam dla Ciebie te propozycje:\n"
                    "1. Coco — Chłopiec trafia do Krainy Umarłych. Dane katalogowe: Animacja.\n"
                    "2. Odlot — Senior rusza w podróż. Dane katalogowe: Animacja."
                ),
            },
        )

        run = self.agent.answer_content_question(
            "O czym jest pierwsza propozycja?",
            (),
            history,
        )

        self.assertIn("Coco — Chłopiec trafia", run.message)
        self.assertNotIn("Odlot", run.message)

    def test_does_not_claim_happy_end_without_catalog_data(self):
        run = self.agent.answer_content_question(
            "Czy każdy ma happy ending?",
            (),
        )

        self.assertIn("nie mogę rzetelnie potwierdzić", run.message.casefold())

    def test_answers_enriched_catalog_questions(self):
        enriched = RetrievalCandidate(
            **{
                **candidate(1, title="Film testowy").__dict__,
                "metadata": {
                    "runtimeMinutes": 98,
                    "directors": ["Jan Reżyser"],
                    "cast": ["Anna Aktorka", "Piotr Aktor"],
                    "ageRating": "12",
                },
            }
        )

        director = self.agent.answer_content_question(
            "Kto reżyserował Film testowy?", (enriched,)
        )
        cast = self.agent.answer_content_question(
            "Kto gra w Film testowy?", (enriched,)
        )
        age = self.agent.answer_content_question(
            "Od ilu lat jest Film testowy?", (enriched,)
        )

        self.assertIn("Jan Reżyser", director.message)
        self.assertIn("Anna Aktorka", cast.message)
        self.assertIn("12", age.message)

    def test_stored_gore_avoidance_does_not_warn_on_unrelated_prompt(self):
        run = self.agent.run(
            "Poleć lekki serial.",
            profile(avoid=("Gore",)),
            self.selected,
        )

        self.assertNotIn("gore", run.message.casefold())


class RecommendationGraphTests(SimpleTestCase):
    @patch("backend.recommendation_agents.graph.build_profiling_input")
    @patch("backend.recommendation_agents.graph.ExplanationAgent.run")
    @patch("backend.recommendation_agents.graph.RankingAgent.run")
    @patch("backend.recommendation_agents.graph.RetrievalAgent.run")
    @patch("backend.recommendation_agents.graph.ProfilingAgent.run")
    def test_runs_all_four_agents_in_order(
        self, profiling_run, retrieval_run, ranking_run, explanation_run, build_input
    ):
        profiling_input = ProfilingAgentInput(current_request="Thriller")
        profiling_result = ProfilingAgentRun(profile(), "model", 1, 1, 1)
        retrieved = RetrievalAgentRun((candidate(1),), "semantic", "Thriller")
        ranked_item = RankedCandidate(candidate(1), 0.9, 0.8, 0.865, "selected", 1, "Pasuje")
        ranked = RankingAgentRun((ranked_item,), "model", 1, 1)
        explained = ExplanationAgentRun("Odpowiedź", (), "model", 1, 1)
        build_input.return_value = profiling_input
        profiling_run.return_value = profiling_result
        retrieval_run.return_value = retrieved
        ranking_run.return_value = ranked
        explanation_run.return_value = explained
        client = MagicMock(model="model", embedding_model="embed")

        result = build_recommendation_graph(client).invoke(
            {"user": object(), "current_request": "Thriller", "conversation_history": ()}
        )

        self.assertEqual(result["explanation"].message, "Odpowiedź")
        profiling_run.assert_called_once()
        retrieval_run.assert_called_once()
        ranking_run.assert_called_once()
        explanation_run.assert_called_once()

    @patch("backend.recommendation_agents.graph.build_profiling_input")
    @patch("backend.recommendation_agents.graph.RetrievalAgent.run")
    @patch("backend.recommendation_agents.graph.ProfilingAgent.run")
    def test_stops_for_clarification_without_retrieval(self, profiling_run, retrieval_run, build_input):
        build_input.return_value = ProfilingAgentInput(current_request="Poleć coś")
        profiling_run.return_value = ProfilingAgentRun(
            profile(needs_clarification=True, clarification_question="Film czy serial?"),
            "model", 1, 1, 1,
        )
        client = MagicMock(model="model", embedding_model="embed")

        result = build_recommendation_graph(client).invoke(
            {"user": object(), "current_request": "Poleć coś"}
        )

        self.assertEqual(result["explanation"].message, "Film czy serial?")
        retrieval_run.assert_not_called()

    @patch("backend.recommendation_agents.graph.build_profiling_input")
    @patch("backend.recommendation_agents.graph.ExplanationAgent.answer_content_question")
    @patch("backend.recommendation_agents.graph.RankingAgent.run")
    @patch("backend.recommendation_agents.graph.RetrievalAgent.run")
    @patch("backend.recommendation_agents.graph.ProfilingAgent.run")
    def test_content_question_retrieves_context_without_ranking(
        self,
        profiling_run,
        retrieval_run,
        ranking_run,
        answer_content_question,
        build_input,
    ):
        history = (
            {"role": "assistant", "content": "Poleciłem film Zagadka."},
        )
        build_input.return_value = ProfilingAgentInput(
            current_request="O czym jest ten film?",
            conversation_history=history,
        )
        profiling_run.return_value = ProfilingAgentRun(
            profile(
                intent="content_question",
                needs_clarification=False,
                clarification_question=None,
            ),
            "model",
            1,
            1,
            1,
        )
        retrieved = RetrievalAgentRun((candidate(1),), "semantic", "Zagadka")
        retrieval_run.return_value = retrieved
        answer_content_question.return_value = ExplanationAgentRun(
            "Opis fabuły.", (), "model", 1, 1
        )
        client = MagicMock(model="model", embedding_model="embed")

        result = build_recommendation_graph(client).invoke(
            {
                "user": object(),
                "current_request": "O czym jest ten film?",
                "conversation_history": history,
            }
        )

        self.assertEqual(result["explanation"].message, "Opis fabuły.")
        retrieval_run.assert_called_once()
        ranking_run.assert_not_called()
        answer_content_question.assert_called_once_with(
            "O czym jest ten film?",
            retrieved.candidates,
            history,
        )
