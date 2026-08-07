from time import monotonic
from typing import Any, Callable, TypedDict
from langgraph.graph import END, START, StateGraph
from backend.api.models import BusinessUser
from backend.ollama import OllamaClient
from backend.recommendation_agents.explanation import (
    ExplanationAgent,
    ExplanationAgentRun,
)
from backend.recommendation_agents.profiling import (
    ProfilingAgent,
    ProfilingAgentInput,
    ProfilingAgentRun,
    build_profiling_input,
)
from backend.recommendation_agents.ranking import RankingAgent, RankingAgentRun
from backend.recommendation_agents.retrieval import RetrievalAgent, RetrievalAgentRun


GRAPH_VERSION = "recommendation-agents-v2"


class RecommendationGraphState(TypedDict, total=False):
    user: BusinessUser
    current_request: str
    conversation_history: tuple[dict[str, str], ...]
    profiling_input: ProfilingAgentInput
    profiling: ProfilingAgentRun
    retrieval: RetrievalAgentRun
    ranking: RankingAgentRun
    explanation: ExplanationAgentRun


ExecutionObserver = Callable[
    [str, str, dict[str, Any], dict[str, Any], int | None],
    None,
]


def build_recommendation_graph(
    client: OllamaClient,
    *,
    execution_observer: ExecutionObserver | None = None,
):
    profiling_agent = ProfilingAgent(client)
    retrieval_agent = RetrievalAgent(client if client.embedding_model else None)
    ranking_agent = RankingAgent(client)
    explanation_agent = ExplanationAgent(client)

    def observed(agent_type, input_snapshot, operation, serialize):
        if execution_observer:
            execution_observer(agent_type, "running", input_snapshot, {}, None)
        started = monotonic()
        try:
            result = operation()
        except Exception as error:
            duration_ms = round((monotonic() - started) * 1000)
            if execution_observer:
                execution_observer(
                    agent_type,
                    "failed",
                    input_snapshot,
                    {"error": type(error).__name__},
                    duration_ms,
                )
            raise
        duration_ms = round((monotonic() - started) * 1000)
        if execution_observer:
            execution_observer(
                agent_type,
                "success",
                input_snapshot,
                serialize(result),
                duration_ms,
            )
        return result

    def profiling_node(state: RecommendationGraphState):
        agent_input = build_profiling_input(
            state["user"],
            state["current_request"],
            conversation_history=state.get("conversation_history", ()),
        )
        run = observed(
            "profiling",
            {"current_request": state["current_request"]},
            lambda: profiling_agent.run(agent_input),
            lambda result: result.as_dict(),
        )
        return {
            "profiling_input": agent_input,
            "profiling": run,
        }

    def route_after_profiling(state: RecommendationGraphState):
        output = state["profiling"].output
        if output.intent == "recommendation" and not output.needs_clarification:
            return "retrieve"
        return "explain"

    def retrieval_node(state: RecommendationGraphState):
        preferences = tuple(
            str(item.get("preference_value", ""))
            for item in state["profiling_input"].stored_preferences
            if item.get("polarity", 0) > 0
        )
        run = observed(
            "retrieval",
            {"profiling": state["profiling"].output.as_dict()},
            lambda: retrieval_agent.run(
                state["current_request"],
                state["profiling"].output,
                preference_hints=preferences,
            ),
            lambda result: result.as_dict(),
        )
        return {"retrieval": run}

    def ranking_node(state: RecommendationGraphState):
        run = observed(
            "ranking",
            {
                "candidate_ids": [
                    item.content_id for item in state["retrieval"].candidates
                ]
            },
            lambda: ranking_agent.run(
                state["current_request"],
                state["profiling"].output,
                state["retrieval"].candidates,
            ),
            lambda result: result.as_dict(),
        )
        return {"ranking": run}

    def explanation_node(state: RecommendationGraphState):
        profile = state["profiling"].output
        if profile.needs_clarification:
            run = observed(
                "explanation",
                {"reason": "clarification_required"},
                lambda: ExplanationAgentRun(
                    profile.clarification_question or "Jakiego filmu lub serialu szukasz?",
                    (), client.model, None, None, "fallback", "clarification_required",
                ),
                lambda result: result.as_dict(),
            )
            return {"explanation": run}
        if profile.intent != "recommendation":
            if profile.intent == "recall":
                previous_answer = next(
                    (
                        item.get("content", "")
                        for item in reversed(state.get("conversation_history", ()))
                        if item.get("role") == "assistant"
                    ),
                    "",
                )
                message = (
                    f"Wcześniej odpowiedziałem: {previous_answer[:1800]}"
                    if previous_answer
                    else "W tej rozmowie nie ma jeszcze wcześniejszej rekomendacji."
                )
                reason = "recall"
            else:
                message = "Mogę pomóc w wyborze filmu lub serialu."
                reason = "non_recommendation_intent"
            run = observed(
                "explanation",
                {"reason": reason},
                lambda: ExplanationAgentRun(
                    message,
                    (), client.model, None, None, "fallback", reason,
                ),
                lambda result: result.as_dict(),
            )
            return {"explanation": run}
        run = observed(
            "explanation",
            {
                "selected_candidate_ids": [
                    item.candidate.content_id for item in state["ranking"].selected
                ]
            },
            lambda: explanation_agent.run(
                state["current_request"],
                profile,
                state["ranking"].selected,
            ),
            lambda result: result.as_dict(),
        )
        return {"explanation": run}

    graph = StateGraph(RecommendationGraphState)
    graph.add_node("profile", profiling_node)
    graph.add_node("retrieve", retrieval_node)
    graph.add_node("rank", ranking_node)
    graph.add_node("explain", explanation_node)
    graph.add_edge(START, "profile")
    graph.add_conditional_edges(
        "profile",
        route_after_profiling,
        {"retrieve": "retrieve", "explain": "explain"},
    )
    graph.add_edge("retrieve", "rank")
    graph.add_edge("rank", "explain")
    graph.add_edge("explain", END)
    return graph.compile()
