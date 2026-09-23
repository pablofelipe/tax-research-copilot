from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt

from app.core.ports import LLMPort, RetrievalPort
from app.core.schemas import CONFIDENCE_THRESHOLD
from app.graph.critic import Critic
from app.graph.evaluator import EvaluationResult, Evaluator
from app.graph.planner import Planner
from app.graph.report_generator import ReportGenerator
from app.graph.researcher import Researcher
from app.graph.state import GraphState


def build_graph(
    llm: LLMPort,
    retrieval: RetrievalPort,
    *,
    threshold: float = CONFIDENCE_THRESHOLD,
    checkpointer: Any = None,
) -> CompiledStateGraph:
    planner = Planner(llm)
    researcher = Researcher(retrieval, llm)
    critic = Critic(llm)
    evaluator = Evaluator(threshold)
    report_generator = ReportGenerator()

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
    graph.add_node("plan", plan_node)
    graph.add_node("research", research_node)
    graph.add_node("critique", critique_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("report", report_node)

    graph.add_edge(START, "plan")
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
