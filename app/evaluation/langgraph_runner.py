import uuid

from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from app.core.schemas import TaxResearchResponse


class LangGraphRunner:
    """GraphRunner adapter over a compiled StateGraph. A human-review
    pause is auto-resumed with an "approved" decision so evaluation
    always ends with a graded response — an evaluation-only convenience,
    never a stand-in for real human review in production.
    """

    def __init__(self, graph: CompiledStateGraph):
        self._graph = graph

    def run(self, query: str) -> TaxResearchResponse:
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        result = self._graph.invoke({"query": query}, config=config)

        if "__interrupt__" in result:
            result = self._graph.invoke(Command(resume="approved"), config=config)

        return result["response"]
