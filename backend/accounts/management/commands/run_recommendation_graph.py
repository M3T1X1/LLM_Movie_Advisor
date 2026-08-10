import json

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError

from backend.api.models import BusinessUser
from backend.ollama import OllamaError, get_ollama_client
from backend.recommendation_agents.explanation import ExplanationAgentError
from backend.recommendation_agents.graph import GRAPH_VERSION, build_recommendation_graph
from backend.recommendation_agents.profiling import ProfilingAgentError
from backend.recommendation_agents.ranking import RankingAgentError


class Command(BaseCommand):
    help = "Runs the four-agent recommendation graph without database persistence."

    def add_arguments(self, parser):
        parser.add_argument("prompt", nargs="+")
        parser.add_argument("--user-id", type=int, required=True)
        parser.add_argument(
            "--summary",
            action="store_true",
            help="Print only stage sources, selected titles, and the final answer.",
        )

    def handle(self, *args, **options):
        prompt = " ".join(options["prompt"]).strip()
        user = BusinessUser.objects.filter(pk=options["user_id"]).first()
        if not prompt:
            raise CommandError("Prompt cannot be empty.")
        if user is None:
            raise CommandError("Business user does not exist.")
        try:
            client = get_ollama_client()
            available_models = client.list_models()
            if not client.is_model_available(client.model, available_models):
                raise CommandError(
                    f"Ollama model `{client.model}` is not downloaded."
                )
            result = build_recommendation_graph(client).invoke(
                {"user": user, "current_request": prompt, "conversation_history": ()}
            )
        except (
            DatabaseError,
            OllamaError,
            ProfilingAgentError,
            RankingAgentError,
            ExplanationAgentError,
            ValueError,
        ) as error:
            raise CommandError(str(error)) from error

        if options["summary"]:
            payload = {
                "graph_version": GRAPH_VERSION,
                "profiling_source": result["profiling"].source,
                "profiling": result["profiling"].output.as_dict(),
                "retrieval_mode": (
                    result["retrieval"].retrieval_mode
                    if result.get("retrieval")
                    else None
                ),
                "retrieved_count": (
                    len(result["retrieval"].candidates)
                    if result.get("retrieval")
                    else 0
                ),
                "ranking_source": (
                    result["ranking"].source if result.get("ranking") else None
                ),
                "selected": [
                    {
                        "content_id": item.candidate.content_id,
                        "title": item.candidate.title,
                        "final_score": item.final_score,
                        "reason": item.decision_reason,
                    }
                    for item in (
                        result["ranking"].selected
                        if result.get("ranking")
                        else ()
                    )
                ],
                "answer": result["explanation"].as_dict(),
            }
        else:
            payload = {
                "graph_version": GRAPH_VERSION,
                "profiling": result["profiling"].output.as_dict(),
                "retrieval": (
                    result["retrieval"].as_dict()
                    if result.get("retrieval")
                    else None
                ),
                "ranking": (
                    [item.as_dict() for item in result["ranking"].candidates]
                    if result.get("ranking")
                    else []
                ),
                "answer": result["explanation"].as_dict(),
            }
        self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
