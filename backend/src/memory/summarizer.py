"""
Message summarization for long conversation histories.

When a workflow's message list grows beyond a threshold, older messages
are compressed into a single summary using an LLM. This keeps the context
window manageable while preserving important information from earlier
turns.

Design decisions
----------------
Why LLM-based summarization (not truncation):
    Truncation (dropping old messages) loses information permanently.
    Summarization preserves the key points — decisions made, preferences
    expressed, requirements identified — in compressed form. The cost is
    one cheap LLM call (Haiku/Llama 8B via TaskType.GENERAL).

Why a threshold-based approach:
    Summarization is triggered only when the message count exceeds
    DEFAULT_MAX_MESSAGES. Below that threshold, messages are returned
    unchanged — no unnecessary LLM calls. The threshold is configurable
    per-workflow via the max_messages parameter.

Why the split strategy (summarize old, keep recent):
    Recent messages contain the immediate context the agent needs (latest
    user input, last assistant response). Older messages contain background
    context that can be compressed. By summarizing only the older half and
    keeping recent messages verbatim, we get the best of both worlds.

Why a graph node wrapper:
    LangGraph graphs operate on state dicts. The summarize_if_needed()
    function reads state["messages"], calls the summarizer if needed, and
    returns a state update. Workflows add it as an optional node between
    other nodes.

Usage
-----
In a LangGraph workflow:
    from src.memory.summarizer import summarize_if_needed

    graph.add_node("summarize", summarize_if_needed)
    graph.add_edge("some_node", "summarize")
    graph.add_edge("summarize", "next_node")

Standalone:
    from src.memory.summarizer import summarize_messages

    compressed = await summarize_messages(long_message_list, max_messages=10)
"""

import structlog
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from src.llm.manager import get_model_manager
from src.llm.models import TaskType

logger = structlog.get_logger()

DEFAULT_MAX_MESSAGES = 10

SUMMARIZATION_PROMPT = """\
You are a conversation summarizer. Below is a sequence of messages from \
a conversation between a user and an AI assistant working on a job \
application task.

Summarize the key information from these messages into a concise paragraph. \
Focus on:
- Decisions made (job targets, preferences, requirements)
- Important facts mentioned (skills, experience, company details)
- Feedback given (what the user liked/disliked, revision requests)
- Current status of the task

Be factual and concise. Do not add opinions or new information.

Messages to summarize:
{messages}"""


async def summarize_messages(
    messages: list[BaseMessage],
    max_messages: int = DEFAULT_MAX_MESSAGES,
) -> list[BaseMessage]:
    """
    Compress older messages into a summary if the list exceeds the threshold.

    If len(messages) <= max_messages, returns the list unchanged (no LLM call).

    Otherwise, splits the list into old and recent halves, summarizes the
    old messages with an LLM, and returns [SystemMessage(summary)] + recent.

    Args:
        messages: The full message history.
        max_messages: Threshold above which summarization is triggered.

    Returns:
        The original messages (if under threshold) or a compressed list
        with a summary SystemMessage followed by recent messages.
    """
    if len(messages) <= max_messages:
        return messages

    # Split: summarize the older half, keep the recent half verbatim.
    split_point = len(messages) // 2
    old_messages = messages[:split_point]
    recent_messages = messages[split_point:]

    # Format old messages for the summarization prompt.
    formatted_messages = "\n".join(
        f"[{msg.__class__.__name__}]: {msg.content}" for msg in old_messages
    )

    prompt = SUMMARIZATION_PROMPT.format(messages=formatted_messages)

    try:
        manager = get_model_manager()
        model = manager.get_model(TaskType.GENERAL)
        response = await model.ainvoke(prompt)
        summary_text = response.content

        logger.debug(
            "messages_summarized",
            original_count=len(messages),
            summarized_count=len(old_messages),
            kept_count=len(recent_messages),
        )

        return [
            SystemMessage(content=f"Summary of earlier conversation:\n{summary_text}"),
            *recent_messages,
        ]
    except Exception:
        # If summarization fails, return the original messages rather than
        # crashing the workflow. The conversation will be longer than ideal
        # but still functional.
        logger.warning(
            "summarization_failed",
            message_count=len(messages),
            exc_info=True,
        )
        return messages


async def summarize_if_needed(
    state: dict,
    config: RunnableConfig,
) -> dict:
    """
    LangGraph node that summarizes messages if they exceed the threshold.

    Reads state["messages"], calls summarize_messages(), and returns a
    state update if summarization occurred. Returns an empty dict if
    no summarization was needed (keeping the state unchanged).

    This node is optional — workflows add it only if they expect long
    conversations (e.g., the interview prep workflow with many Q&A turns).
    """
    messages = state.get("messages", [])
    if len(messages) <= DEFAULT_MAX_MESSAGES:
        return {}

    summarized = await summarize_messages(messages)
    return {"messages": summarized}
