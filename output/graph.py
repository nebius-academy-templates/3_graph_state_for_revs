from langgraph.graph import END, StateGraph

from nodes import (
    bug_detector_node,
    improvement_advisor_node,
    security_auditor_node,
    style_reviewer_node,
    summarizer_node,
)
from state import ReviewState

# ── conditional edges ───────────────────────────────────────────────────────
def security_gate(state: ReviewState) -> str:
    """
    Called after security_auditor_node completes.

    Returns:
      "END"        — security issues found, review is blocked
      "summarizer" — no issues, continue to summarizer
    """
    if state.get("security_issues"):
        return "END"
    return "summarizer"


def quality_router(state: ReviewState) -> str:
    """
    Called after summarizer_node completes.

    Returns:
      "END"          — score is good enough, or we've hit the retry limit
      "bug_detector" — score too low, retry the full chain
    """

    score = state.get("score", 0)
    retry_count = state.get("retry_count", 0)

    if score >= 8:
        return "END"
    if retry_count >= 2:          # forced exit — graph never loops forever
        return "END"
    return "bug_detector"         # retry the full specialist chain


# ── graph builder ────────────────────────────────────────────────────────────
def build_graph() -> StateGraph:
    graph = StateGraph(ReviewState)

    # nodes
    graph.add_node("bug_detector", bug_detector_node)
    graph.add_node("style_reviewer", style_reviewer_node)
    graph.add_node("improvement_advisor", improvement_advisor_node)
    graph.add_node("security_auditor", security_auditor_node)
    graph.add_node("summarizer", summarizer_node)

    # entry point
    graph.set_entry_point("bug_detector")

    # direct edges — deterministic, always run in this order
    graph.add_edge("bug_detector", "style_reviewer")
    graph.add_edge("style_reviewer", "improvement_advisor")
    graph.add_edge("improvement_advisor", "security_auditor")

    # conditional edge — security_gate blocks the pipeline if issues are found
    graph.add_conditional_edges(
        "security_auditor",
        security_gate,
        {
            "END": END,
            "summarizer": "summarizer",
        },
    )

    # conditional edge — quality_router decides what happens after summarizer
    graph.add_conditional_edges(
        "summarizer",
        quality_router,
        {
            "END": END,
            "bug_detector": "bug_detector",
        },
    )

    return graph.compile()


# built once at import time
compiled_graph = build_graph()
