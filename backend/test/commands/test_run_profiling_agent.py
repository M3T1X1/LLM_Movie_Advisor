import json
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from backend.recommendation_agents.profiling import (
    ProfilingAgentInput,
    ProfilingAgentOutput,
    ProfilingAgentRun,
    ProfilingConstraints,
)


class RunProfilingAgentCommandTests(SimpleTestCase):
    def setUp(self):
        self.user_id = 17

    @patch(
        "backend.accounts.management.commands.run_profiling_agent.build_profiling_input"
    )
    @patch(
        "backend.accounts.management.commands.run_profiling_agent.BusinessUser.objects.filter"
    )
    @patch(
        "backend.accounts.management.commands.run_profiling_agent.ProfilingAgent"
    )
    @patch(
        "backend.accounts.management.commands.run_profiling_agent.get_ollama_client"
    )
    def test_prints_structured_agent_output(
        self,
        mocked_get_client,
        mocked_agent,
        mocked_filter,
        mocked_build_input,
    ):
        mocked_filter.return_value.first.return_value = object()
        mocked_build_input.return_value = ProfilingAgentInput(
            current_request="Lekki serial komediowy"
        )
        client = mocked_get_client.return_value
        client.model = "llama3.1:8b"
        client.has_configured_model.return_value = True
        mocked_agent.return_value.run.return_value = ProfilingAgentRun(
            output=ProfilingAgentOutput(
                intent="recommendation",
                mood="lekki",
                media_types=("tv",),
                genres=("komedia",),
                themes=(),
                avoid=(),
                reference_titles=(),
                constraints=ProfilingConstraints(None, None, None, None),
                needs_clarification=False,
                clarification_question=None,
                confidence=0.8,
                evidence=("lekki serial",),
            ),
            model="llama3.1:8b",
            prompt_tokens=20,
            generated_tokens=10,
            total_duration_ns=100,
        )
        stdout = StringIO()
        stderr = StringIO()

        call_command(
            "run_profiling_agent",
            "Lekki",
            "serial",
            "komediowy",
            user_id=self.user_id,
            stdout=stdout,
            stderr=stderr,
        )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["intent"], "recommendation")
        self.assertEqual(payload["media_types"], ["tv"])
        self.assertIn("prompt_tokens=20", stderr.getvalue())

    @patch(
        "backend.accounts.management.commands.run_profiling_agent.BusinessUser.objects.filter"
    )
    def test_rejects_unknown_business_user(self, mocked_filter):
        mocked_filter.return_value.first.return_value = None
        with self.assertRaisesMessage(CommandError, "does not exist"):
            call_command(
                "run_profiling_agent",
                "Poleć film",
                user_id=999999,
            )

