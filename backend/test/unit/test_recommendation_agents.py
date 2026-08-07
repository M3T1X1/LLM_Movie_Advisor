import json
from unittest.mock import MagicMock, call, patch

from django.test import SimpleTestCase, override_settings

from backend.ollama import OllamaChatResponse
from backend.recommendation_agents.explanation import (
    ExplanationAgent,
    ExplanationAgentError,
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

    def test_missing_runtime_does_not_remove_candidate(self):
        output = profile(
            constraints=ProfilingConstraints(100, None, None, None),
        )
        content = MagicMock(metadata={})

        self.assertTrue(RetrievalAgent._runtime_matches(content, output))

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
        self.assertEqual(run.source, "fallback")

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


class ExplanationAgentTests(SimpleTestCase):
    def setUp(self):
        self.client = MagicMock(model="llama3.1:8b")
        base = candidate(1)
        self.selected = (
            RankedCandidate(base, 0.9, 0.8, 0.865, "selected", 1, "Pasuje."),
        )
        self.agent = ExplanationAgent(self.client)

    def test_explains_each_selected_candidate(self):
        self.client.chat.return_value = response(
            {"message": "Mam dla Ciebie jeden tytuł.", "explanations": [{"content_id": 1, "explanation": "Mroczna tajemnica odpowiada prośbie."}]}
        )
        run = self.agent.run("Mroczny thriller", profile(), self.selected)

        self.assertEqual(run.message, "Mam dla Ciebie jeden tytuł.")
        self.assertEqual(run.explanations[0].content_id, 1)
        self.assertEqual(
            run.explanations[0].explanation,
            "Mroczna tajemnica odpowiada prośbie.",
        )
        self.assertEqual(run.model, "llama3.1:8b")
        self.assertEqual(run.prompt_tokens, 20)
        self.assertEqual(run.generated_tokens, 10)
        self.client.chat.assert_called_once()
        messages = self.client.chat.call_args.args[0]
        payload = json.loads(messages[1]["content"])
        self.assertEqual(payload["current_request"], "Mroczny thriller")
        self.assertEqual(payload["selected_candidates"][0]["content_id"], 1)
        self.assertEqual(
            self.client.chat.call_args.kwargs["options"]["temperature"],
            0,
        )

    def test_falls_back_for_explanation_of_unknown_candidate(self):
        self.client.chat.return_value = response(
            {"message": "Wynik.", "explanations": [{"content_id": 999, "explanation": "Nieznany film."}]}
        )
        run = self.agent.run("Thriller", profile(), self.selected)

        self.assertIn("Film 1", run.message)
        self.assertEqual(run.explanations[0].content_id, 1)

    def test_falls_back_for_invalid_json(self):
        self.client.chat.return_value = OllamaChatResponse(
            content="{invalid-json",
            model="llama3.1:8b",
            done_reason="stop",
            total_duration_ns=100,
            prompt_eval_count=20,
            eval_count=10,
        )

        run = self.agent.run("Thriller", profile(), self.selected)

        self.assertIn("Film 1", run.message)
        self.assertEqual(run.explanations[0].content_id, 1)
        self.assertEqual(run.prompt_tokens, 20)

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

        self.assertIn("Nie mogę potwierdzić limitu 100 minut", run.message)
        self.client.chat.assert_not_called()


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
