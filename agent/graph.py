"""
LangGraph graph definition for the BDD Agent.

Flow:
  generate_tests → human_review → generate_steps → run_tests → report

Human-in-loop is handled via LangGraph's interrupt() in the human_review node.
The graph uses a MemorySaver checkpointer so state is persisted across interrupts.
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agent.state import AgentState
from agent.nodes.generate_tests import generate_tests_node
from agent.nodes.human_review import human_review_node
from agent.nodes.generate_steps import generate_steps_node
from agent.nodes.run_tests import run_tests_node
from agent.nodes.report import report_node


def should_continue_after_review(state: AgentState) -> str:
    """
    Conditional edge: after human review, only continue if scenarios were approved.
    """
    approved = state.get("approved_scenarios", [])
    if not approved:
        return "end"
    return "generate_steps"


def should_continue_after_generation(state: AgentState) -> str:
    """
    Conditional edge: stop if an error occurred during step generation.
    """
    if state.get("error"):
        return "end"
    return "run_tests"


def build_graph() -> StateGraph:
    """
    Constructs and compiles the BDD Agent LangGraph.
    Returns a compiled graph with MemorySaver checkpointer for interrupt support.
    """
    builder = StateGraph(AgentState)

    # --- Register nodes ---
    builder.add_node("generate_tests", generate_tests_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("generate_steps", generate_steps_node)
    builder.add_node("run_tests", run_tests_node)
    builder.add_node("report", report_node)

    # --- Entry point ---
    builder.set_entry_point("generate_tests")

    # --- Edges ---
    builder.add_edge("generate_tests", "human_review")

    builder.add_conditional_edges(
        "human_review",
        should_continue_after_review,
        {
            "generate_steps": "generate_steps",
            "end": END
        }
    )

    builder.add_conditional_edges(
        "generate_steps",
        should_continue_after_generation,
        {
            "run_tests": "run_tests",
            "end": END
        }
    )

    builder.add_edge("run_tests", "report")
    builder.add_edge("report", END)

    # Compile with memory checkpointer (required for interrupt/resume)
    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer, interrupt_before=["human_review"])

    return graph
