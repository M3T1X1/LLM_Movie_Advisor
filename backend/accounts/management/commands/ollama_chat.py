from django.core.management.base import BaseCommand, CommandError

from backend.ollama import OllamaError, get_ollama_client


DEFAULT_SYSTEM_PROMPT = (
    "Jesteś polskojęzycznym doradcą filmowym. Odpowiadaj zwięźle i jasno. "
    "To jest test połączenia z modelem, więc nie twierdź, że masz dostęp do "
    "katalogu aplikacji ani danych użytkownika."
)


class Command(BaseCommand):
    help = "Sends one non-streaming test message to the configured Ollama model."

    def add_arguments(self, parser):
        parser.add_argument(
            "prompt",
            nargs="+",
            help="Message sent to the configured local chat model.",
        )
        parser.add_argument(
            "--system",
            default=DEFAULT_SYSTEM_PROMPT,
            help="System instruction used for this test request.",
        )

    def handle(self, *args, **options):
        prompt = " ".join(options["prompt"]).strip()
        system_prompt = options["system"].strip()
        if not prompt:
            raise CommandError("Prompt cannot be empty.")
        if not system_prompt:
            raise CommandError("System prompt cannot be empty.")

        try:
            client = get_ollama_client()
            if not client.has_configured_model():
                raise CommandError(
                    f"Ollama model `{client.model}` is not downloaded."
                )
            response = client.chat(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ]
            )
        except OllamaError as error:
            raise CommandError(str(error)) from error

        self.stdout.write(response.content)
        self.stderr.write(
            "Ollama response: "
            f"model={response.model}, "
            f"prompt_tokens={response.prompt_eval_count or 0}, "
            f"generated_tokens={response.eval_count or 0}."
        )
