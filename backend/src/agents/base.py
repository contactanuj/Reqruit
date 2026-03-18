"""
BaseAgent — abstract base class for all LLM-powered agents.

Every agent in the system (13 total across 4 workflows) inherits from BaseAgent.
The class handles the complete LLM call lifecycle so subclasses only need to
define what messages to send and how to interpret the response.

Design decisions
----------------
Why __call__ as the main interface (not a method like .run() or .execute()):
    LangGraph's StateGraph.add_node() expects a callable — either a function
    or an object with __call__. Making BaseAgent callable means agents plug
    directly into the graph: `builder.add_node("analyst", RequirementsAnalyst())`.
    No adapter functions or lambdas needed.

Why user_id comes from config (not state):
    config["configurable"]["user_id"] is the standard LangGraph convention for
    session metadata that stays constant throughout a workflow invocation.
    Putting user_id in state would mean every state TypedDict needs it, and
    it would get serialized into every checkpoint. Config is the right place
    for metadata that identifies the session but doesn't affect graph logic.

Why the full try/except wraps the LLM call:
    LLM providers can fail in many ways — network errors, rate limits, invalid
    responses, context length exceeded. BaseAgent catches all exceptions,
    records the failure on the circuit breaker (so the provider gets skipped
    for subsequent calls), and re-raises as LLMProviderError. This ensures
    consistent error handling across all 13 agents without duplicating
    try/except blocks in each subclass.

Usage
-----
Subclass implementation:

    class RequirementsAnalyst(BaseAgent):
        def __init__(self):
            super().__init__(
                name="requirements_analyst",
                task_type=TaskType.DATA_EXTRACTION,
                system_prompt="Extract key requirements from the job description.",
            )

        def build_messages(self, state):
            return [HumanMessage(content=state["job_description"])]

        def process_response(self, response, state):
            return {"requirements_analysis": response.content}

In a LangGraph workflow:

    analyst = RequirementsAnalyst()
    builder.add_node("analyze", analyst)
"""

from abc import ABC, abstractmethod

import structlog
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage

from src.core.exceptions import LLMProviderError
from src.llm.manager import get_model_manager
from src.llm.models import TaskType

logger = structlog.get_logger()


class BaseAgent(ABC):
    """
    Abstract base class for all LLM-powered agents.

    Provides the complete LLM call lifecycle: model selection via the routing
    table, system prompt injection, cost tracking, and circuit breaker
    integration. Subclasses define only the task-specific logic — what messages
    to send (build_messages) and how to interpret the response (process_response).

    Attributes:
        name: Human-readable agent identifier, used in cost records and logs.
        task_type: Determines which model gets selected from the routing table.
        system_prompt: Prepended to every LLM call as a SystemMessage.
    """

    def __init__(
        self, name: str, task_type: TaskType, system_prompt: str
    ) -> None:
        self.name = name
        self.task_type = task_type
        self.system_prompt = system_prompt

    async def __call__(
        self, state: dict, config: dict | None = None
    ) -> dict:
        """
        Execute the agent as a LangGraph node.

        This is the method LangGraph calls when the graph reaches this node.
        It orchestrates the full lifecycle:
        1. Resolve user_id from the LangGraph config
        2. Get the right model for this task type (with fallback)
        3. Build the message list: system prompt + subclass messages
        4. Invoke the model with cost tracking
        5. Record success/failure on the circuit breaker
        6. Delegate response processing to the subclass

        Args:
            state: The current graph state (TypedDict from the workflow).
            config: LangGraph runtime config. Contains user_id at
                config["configurable"]["user_id"].

        Returns:
            A dict of state updates to merge into the graph state.

        Raises:
            LLMProviderError: If the LLM call fails for any reason.
        """
        user_id = _extract_user_id(config)
        manager = get_model_manager()

        model, model_config = manager.get_model_with_config(self.task_type)
        messages = [SystemMessage(content=self.system_prompt)]
        messages.extend(self.build_messages(state))

        callback = manager.create_cost_callback(
            user_id=user_id,
            agent=self.name,
            task_type=self.task_type.value,
        )

        try:
            response: AIMessage = await model.ainvoke(
                messages, config={"callbacks": [callback]}
            )
        except LLMProviderError:
            # Already an LLMProviderError (e.g., from a provider-specific handler).
            # Record the failure and re-raise without wrapping.
            manager.record_failure(model_config.provider)
            raise
        except Exception as exc:
            manager.record_failure(model_config.provider)
            logger.warning(
                "agent_llm_call_failed",
                agent=self.name,
                provider=model_config.provider.value,
                error=str(exc),
            )
            raise LLMProviderError(
                detail=f"Agent '{self.name}' LLM call failed: {exc}",
                provider=model_config.provider.value,
            ) from exc

        manager.record_success(model_config.provider)

        logger.debug(
            "agent_call_completed",
            agent=self.name,
            provider=model_config.provider.value,
            model=model_config.model_name,
        )

        return self.process_response(response, state)

    @abstractmethod
    def build_messages(self, state: dict) -> list[BaseMessage]:
        """
        Build the task-specific messages for the LLM call.

        The system prompt is prepended automatically by __call__ — this method
        should return only the user/assistant messages that convey the task.

        Args:
            state: The current graph state.

        Returns:
            A list of LangChain messages (typically one HumanMessage).
        """

    @abstractmethod
    def process_response(self, response: AIMessage, state: dict) -> dict:
        """
        Process the LLM response into graph state updates.

        Called after a successful LLM invocation. The returned dict is merged
        into the graph state by LangGraph's state update mechanism.

        Args:
            response: The AIMessage returned by the model.
            state: The current graph state (for context if needed).

        Returns:
            A dict of state keys to update.
        """


def extract_json(content: str) -> str:
    """Strip markdown code fences from LLM output, returning the inner text.

    Handles both ```json ... ``` and bare ``` ... ``` fences.  If no
    fences are found the original string is returned unchanged.
    """
    if "```json" in content:
        content = content.split("```json", 1)[1]
        if "```" in content:
            content = content.split("```", 1)[0]
    elif "```" in content:
        content = content.split("```", 1)[1]
        if "```" in content:
            content = content.split("```", 1)[0]
    return content.strip()


def _extract_user_id(config: dict | None) -> str:
    """
    Extract user_id from LangGraph runtime config.

    Falls back to "unknown" if config is missing or doesn't contain a
    user_id. This keeps cost tracking functional even in dev/test scenarios
    where config may be omitted.
    """
    if config is None:
        return "unknown"
    configurable = config.get("configurable", {})
    return configurable.get("user_id", "unknown")
