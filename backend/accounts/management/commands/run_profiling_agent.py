import json

from django.core.management.base import BaseCommand, CommandError

from backend.api.models import BusinessUser
from backend.ollama import OllamaError, get_ollama_client
from backend.recommendation_agents.profiling import (
    ProfilingAgent,
    ProfilingAgentError,
    build_profiling_input,
)


class Command(BaseCommand):
    help = "Runs the profiling and context agent for one existing business user."

    def add_arguments(self, parser):
        parser.add_argument(
            "prompt",
            nargs="+",
            help="Recommendation request analyzed by the profiling agent.",
        )
        parser.add_argument(
            "--user-id",
            type=int,
            required=True,
            help="ID from the app_user table whose profile should be used.",
        )

    def handle(self, *args, **options):
        prompt = " ".join(options["prompt"]).strip()
        if not prompt:
            raise CommandError("Prompt cannot be empty.")
        user = BusinessUser.objects.filter(pk=options["user_id"]).first()
        if user is None:
            raise CommandError("Business user does not exist.")

        try:
            client = get_ollama_client()
            if not client.has_configured_model():
                raise CommandError(
                    f"Ollama model `{client.model}` is not downloaded."
                )
            agent_input = build_profiling_input(user, prompt)
            run = ProfilingAgent(client).run(agent_input)
        except (OllamaError, ProfilingAgentError, ValueError) as error:
            raise CommandError(str(error)) from error

        self.stdout.write(
            json.dumps(run.output.as_dict(), ensure_ascii=False, indent=2)
        )
        self.stderr.write(
            "Profiling agent response: "
            f"model={run.model}, "
            f"prompt_tokens={run.prompt_tokens or 0}, "
            f"generated_tokens={run.generated_tokens or 0}."
        )

