from dataclasses import dataclass

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from backend.api.models import (
    AgentExecution,
    AgentStatus,
    BusinessUser,
    CandidateStatus,
    Conversation,
    Message,
    MessageRole,
    RecommendationRequest,
    RecommendationRun,
    RunCandidate,
    RunStatus,
)
from backend.ollama import OllamaClient
from backend.prompt_security import sanitize_untrusted_history
from backend.recommendation_agents.graph import (
    GRAPH_VERSION,
    build_recommendation_graph,
)


AGENT_SEQUENCE = ("profiling", "retrieval", "ranking", "explanation")


@dataclass(frozen=True)
class PersistentRecommendationResult:
    request: RecommendationRequest
    run: RecommendationRun
    assistant_message: Message
    candidates: tuple[RunCandidate, ...]
    agent_executions: tuple[AgentExecution, ...]


def run_persistent_recommendation(
    *,
    user: BusinessUser,
    conversation: Conversation,
    prompt: str,
    client: OllamaClient,
) -> PersistentRecommendationResult:
    now = timezone.now()
    with transaction.atomic():
        locked = Conversation.objects.select_for_update().get(pk=conversation.pk)
        historical_messages = list(
            Message.objects.filter(conversation=locked)
            .filter(role__in=[MessageRole.USER, MessageRole.ASSISTANT])
            .order_by("-sequence_no")[:10]
        )
        raw_history = [
            {"role": item.role, "content": item.content}
            for item in reversed(historical_messages)
        ]
        history = tuple(sanitize_untrusted_history(raw_history))
        maximum = Message.objects.filter(conversation=locked).aggregate(
            maximum=Max("sequence_no")
        )["maximum"]
        user_message = Message.objects.create(
            conversation=locked,
            role=MessageRole.USER,
            content=prompt,
            sequence_no=(maximum or 0) + 1,
        )
        if not locked.title:
            locked.title = prompt[:255]
        locked.updated_at = now
        locked.save(update_fields=["title", "updated_at"])
        recommendation_request = RecommendationRequest.objects.create(
            conversation=locked,
            trigger_message=user_message,
        )
        recommendation_run = RecommendationRun.objects.create(
            request=recommendation_request,
            status=RunStatus.RUNNING,
            graph_version=GRAPH_VERSION,
            model_name=client.model,
            started_at=now,
        )
        executions = {
            agent_type: AgentExecution.objects.create(
                run=recommendation_run,
                agent_type=agent_type,
                sequence_no=index,
            )
            for index, agent_type in enumerate(AGENT_SEQUENCE, start=1)
        }

    def observe(agent_type, status, input_snapshot, output_snapshot, duration_ms):
        execution = executions[agent_type]
        execution.status = status
        execution.input_snapshot = input_snapshot
        execution.output_snapshot = output_snapshot
        execution.duration_ms = duration_ms
        if status == AgentStatus.RUNNING:
            execution.started_at = timezone.now()
            fields = ["status", "input_snapshot", "started_at"]
        else:
            execution.finished_at = timezone.now()
            fields = [
                "status",
                "input_snapshot",
                "output_snapshot",
                "duration_ms",
                "finished_at",
            ]
        execution.save(update_fields=fields)
        if agent_type == "profiling" and status == AgentStatus.SUCCESS:
            constraints = output_snapshot.get("constraints", {})
            RecommendationRequest.objects.filter(pk=recommendation_request.pk).update(
                mood=output_snapshot.get("mood"),
                extracted_context=output_snapshot,
                constraints=constraints if isinstance(constraints, dict) else {},
            )

    def fail_run() -> None:
        finished_at = timezone.now()
        RecommendationRun.objects.filter(pk=recommendation_run.pk).update(
            status=RunStatus.FAILED,
            finished_at=finished_at,
        )
        AgentExecution.objects.filter(
            run=recommendation_run,
            status__in=[AgentStatus.PENDING, AgentStatus.RUNNING],
        ).update(
            status=AgentStatus.FAILED,
            output_snapshot={"error": "aborted"},
            finished_at=finished_at,
        )

    try:
        graph_result = build_recommendation_graph(
            client,
            execution_observer=observe,
        ).invoke(
            {
                "user": user,
                "current_request": prompt,
                "conversation_history": history,
            }
        )
    except Exception:
        fail_run()
        raise

    profiling = graph_result["profiling"].output
    explanations = {
        item.content_id: item.explanation
        for item in graph_result["explanation"].explanations
    }
    finished_at = timezone.now()
    try:
        with transaction.atomic():
            recommendation_request.mood = profiling.mood
            recommendation_request.extracted_context = profiling.as_dict()
            recommendation_request.constraints = profiling.constraints.__dict__
            recommendation_request.save(
                update_fields=["mood", "extracted_context", "constraints"]
            )
            stored_candidates = tuple(
                RunCandidate.objects.create(
                    run=recommendation_run,
                    content_id=item.candidate.content_id,
                    source_rank=item.candidate.source_rank,
                    relevance_score=item.relevance_score,
                    critic_score=item.critic_score,
                    final_score=item.final_score,
                    status=(
                        CandidateStatus.SELECTED
                        if item.status == "selected"
                        else CandidateStatus.REJECTED
                    ),
                    final_rank=item.final_rank,
                    decision_reason=item.decision_reason,
                    explanation=explanations.get(item.candidate.content_id),
                    metadata_snapshot=item.candidate.as_dict(),
                )
                for item in graph_result.get("ranking", ()).candidates
            ) if graph_result.get("ranking") else ()
            locked = Conversation.objects.select_for_update().get(pk=conversation.pk)
            maximum = Message.objects.filter(conversation=locked).aggregate(
                maximum=Max("sequence_no")
            )["maximum"]
            assistant_message = Message.objects.create(
                conversation=locked,
                role=MessageRole.ASSISTANT,
                content=graph_result["explanation"].message,
                sequence_no=(maximum or 0) + 1,
            )
            locked.updated_at = finished_at
            locked.save(update_fields=["updated_at"])
            recommendation_run.status = RunStatus.COMPLETED
            recommendation_run.finished_at = finished_at
            recommendation_run.save(update_fields=["status", "finished_at"])
            AgentExecution.objects.filter(
                run=recommendation_run,
                status=AgentStatus.PENDING,
            ).update(
                status=AgentStatus.SUCCESS,
                input_snapshot={"skipped": True},
                output_snapshot={"skipped": True},
                started_at=finished_at,
                finished_at=finished_at,
            )
    except Exception:
        fail_run()
        raise

    recommendation_run.refresh_from_db()
    recommendation_request.refresh_from_db()
    return PersistentRecommendationResult(
        request=recommendation_request,
        run=recommendation_run,
        assistant_message=assistant_message,
        candidates=stored_candidates,
        agent_executions=tuple(
            AgentExecution.objects.filter(run=recommendation_run).order_by(
                "sequence_no"
            )
        ),
    )
