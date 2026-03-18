"""
State definition for the negotiation workflow.

Tracks multi-turn negotiation simulation, counter-offer scripts,
and decision framework data across all negotiation graph nodes.
"""

from typing import Annotated

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class NegotiationState(TypedDict):
    """
    Full state for the negotiation workflow.

    Attributes:
        messages: Append-only conversation history for LangGraph.
        offer_details: Dict with offer context (company, role, total comp, locale).
        market_data: Market positioning data (percentile, salary range).
        competing_offers: List of competing offer summaries.
        user_priorities: Dict of negotiation goals (target salary, non-salary priorities).
        simulation_transcript: Turn-by-turn negotiation data (role, content, tactic, feedback).
        user_response: Latest user response for the current turn.
        scripts: Generated counter-offer scripts.
        decision_matrix: Multi-criteria decision framework data.
        feedback: Session-level feedback or summary.
        status: Workflow lifecycle stage (simulating, scripting, deciding, complete).
    """

    messages: Annotated[list, add_messages]
    offer_details: dict
    market_data: dict
    competing_offers: list[dict]
    user_priorities: dict
    simulation_transcript: list[dict]
    user_response: str
    scripts: list[dict]
    decision_matrix: dict
    feedback: str
    status: str
