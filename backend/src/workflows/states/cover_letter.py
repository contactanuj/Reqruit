"""
State definition for the cover letter workflow.

LangGraph graphs are typed via TypedDict — each key in the dict is a channel
that nodes can read from and write to. The Annotated[list, add_messages]
pattern tells LangGraph to *append* new messages rather than replacing the
list, which is essential for accumulating conversation history across nodes.

The status field tracks where the workflow is in its lifecycle. This is useful
for the frontend to display progress and for the human_review node to decide
what to surface to the user.
"""

from typing import Annotated

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class CoverLetterState(TypedDict):
    """
    Full state for the cover letter generation workflow.

    Attributes:
        messages: Append-only conversation history across all nodes.
            Uses the add_messages reducer so each node's messages are appended
            rather than replacing the list.
        job_description: The raw job posting text provided by the user.
        resume_text: The user's resume content (plain text).
        requirements_analysis: Structured analysis from RequirementsAnalyst.
            Populated after the analyze_requirements node runs.
        memory_context: Retrieved context from the memory system (past cover
            letters, resume chunks, etc.). Populated by the retrieve_memories
            node before the writer runs. Empty string if no memories found.
        cover_letter: The generated cover letter text.
            Updated each time CoverLetterWriter runs (including revisions).
        feedback: User feedback from the human review step.
            Empty string until the user requests a revision.
        status: Workflow lifecycle stage. One of:
            - "pending": initial state before any node has run
            - "analyzing": RequirementsAnalyst is processing
            - "writing": CoverLetterWriter is generating
            - "reviewing": paused at human_review, waiting for user input
            - "revision_requested": user asked for changes, looping back
            - "approved": user approved the cover letter, workflow complete
    """

    messages: Annotated[list, add_messages]
    job_description: str
    resume_text: str
    requirements_analysis: str
    memory_context: str
    cover_letter: str
    feedback: str
    status: str
