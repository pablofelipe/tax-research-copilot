from collections.abc import Callable
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt
from opentelemetry import trace

from app.core.ports import LLMPort, RetrievalPort
from app.core.schemas import CONFIDENCE_THRESHOLD
from app.graph.critic import Critic
from app.graph.evaluator import EvaluationResult, Evaluator
from app.graph.guardrail import Guardrail
from app.graph.planner import Planner
from app.graph.report_generator import ReportGenerator
from app.graph.researcher import Researcher
from app.graph.state import GraphState

_tracer = trace.get_tracer("tax_research_copilot.graph")


def _traced(name: str, node: Callable[[GraphState], dict]) -> Callable[[GraphState], dict]:
    """Wraps a node function in its own span, named after the node. A
    no-op unless a TracerProvider has been configured (see
    app.observability.tracing) — safe to leave on in every unit test,
    which never configure one.
    """

    def wrapped(state: GraphState) -> dict:
        with _tracer.start_as_current_span(name):
            return node(state)

    return wrapped


def build_graph(
    llm: LLMPort,
    retrieval: RetrievalPort,
    *,
    threshold: float = CONFIDENCE_THRESHOLD,
    checkpointer: Any = None,
) -> CompiledStateGraph:
    guardrail = Guardrail()
    planner = Planner(llm)
    researcher = Researcher(retrieval, llm)
    critic = Critic(llm)
    evaluator = Evaluator(threshold)
    report_generator = ReportGenerator()

    def guardrail_node(state: GraphState) -> dict:
        return {"in_scope": guardrail.is_in_scope(state["query"])}

    def route_after_guardrail(state: GraphState) -> str:
        return "plan" if state["in_scope"] else "out_of_scope"

    def out_of_scope_node(state: GraphState) -> dict:
        return {"response": guardrail.reject(state["query"])}

    def plan_node(state: GraphState) -> dict:
        return {"sub_questions": planner.plan(state["query"])}

    def research_node(state: GraphState) -> dict:
        # Sequential per sub-question for v1: simpler failure handling and
        # ordering than LangGraph's Send-based fan-out. Revisit if latency
        # from N sequential LLM calls becomes a real constraint.
        sub_answers = [researcher.research(q) for q in state["sub_questions"]]
        return {"sub_answers": sub_answers}

    def critique_node(state: GraphState) -> dict:
        disputed = critic.detect_conflicts(state["sub_answers"])
        return {"disputed_positions": disputed}

    def evaluate_node(state: GraphState) -> dict:
        result = evaluator.evaluate(state["sub_answers"], state["disputed_positions"])
        return {
            "overall_confidence": result.overall_confidence,
            "requires_human_review": result.requires_human_review,
        }

    def route_after_evaluate(state: GraphState) -> str:
        return "human_review" if state["requires_human_review"] else "report"

    def human_review_node(state: GraphState) -> dict:
        # Blocking, not best-effort: interrupt() halts graph execution and,
        # with a checkpointer, persists state so the pause survives a
        # process restart. Resuming requires an explicit Command(resume=...)
        # from outside the graph.
        interrupt(
            {
                "query": state["query"],
                "sub_answers": state["sub_answers"],
                "overall_confidence": state["overall_confidence"],
                "disputed_positions": state["disputed_positions"],
            }
        )
        return {}

    def report_node(state: GraphState) -> dict:
        evaluation = EvaluationResult(
            overall_confidence=state["overall_confidence"],
            requires_human_review=state["requires_human_review"],
        )
        response = report_generator.generate(
            query=state["query"],
            sub_answers=state["sub_answers"],
            disputed_positions=state["disputed_positions"],
            evaluation=evaluation,
        )
        return {"response": response}

    graph = StateGraph(GraphState)
    graph.add_node("guardrail", _traced("guardrail", guardrail_node))
    graph.add_node("out_of_scope", _traced("out_of_scope", out_of_scope_node))
    graph.add_node("plan", _traced("plan", plan_node))
    graph.add_node("research", _traced("research", research_node))
    graph.add_node("critique", _traced("critique", critique_node))
    graph.add_node("evaluate", _traced("evaluate", evaluate_node))
    graph.add_node("human_review", _traced("human_review", human_review_node))
    graph.add_node("report", _traced("report", report_node))

    graph.add_edge(START, "guardrail")
    graph.add_conditional_edges(
        "guardrail",
        route_after_guardrail,
        {"plan": "plan", "out_of_scope": "out_of_scope"},
    )
    graph.add_edge("out_of_scope", END)
    graph.add_edge("plan", "research")
    graph.add_edge("research", "critique")
    graph.add_edge("critique", "evaluate")
    graph.add_conditional_edges(
        "evaluate",
        route_after_evaluate,
        {"human_review": "human_review", "report": "report"},
    )
    graph.add_edge("human_review", "report")
    graph.add_edge("report", END)

    return graph.compile(checkpointer=checkpointer)
