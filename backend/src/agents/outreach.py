"""
Outreach agents — OutreachComposer.

Generates personalized outreach messages tailored to the contact's role
(recruiter, engineer, manager) and the target job/company.
"""

import re

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from src.agents.base import BaseAgent
from src.llm.models import TaskType

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

OUTREACH_COMPOSER_PROMPT = """\
You are an expert networking coach who writes compelling outreach messages \
for job seekers. Given information about the target job, company, and contact \
person, craft a personalized message.

Adapt your tone based on the contact's role:
- Recruiter: formal, highlights qualifications and fit
- Engineer: technical, mentions specific technologies and projects
- Manager: strategic, focuses on team impact and leadership
- Generic: balanced approach when the role is unknown

The message should be concise (3-5 paragraphs), professional, and include:
1. A personalized opening that shows you researched the contact/company
2. Why you are interested in the role specifically
3. 1-2 relevant accomplishments that match the role
4. A clear, low-pressure call to action

Format your response as the message body only — no subject line or signature.\
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class OutreachComposer(BaseAgent):
    """
    Generates personalized outreach messages for networking contacts.

    Reads role_title, company_name, contact_name, contact_role, message_type,
    and job_description from state. Returns the composed message content.
    """

    def __init__(self) -> None:
        super().__init__(
            name="outreach_composer",
            task_type=TaskType.OUTREACH_MESSAGE,
            system_prompt=OUTREACH_COMPOSER_PROMPT,
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        role_title = state.get("role_title", "")
        company_name = state.get("company_name", "")
        contact_name = state.get("contact_name", "")
        contact_role = state.get("contact_role", "")
        message_type = state.get("message_type", "generic")
        job_description = state.get("job_description", "")

        return [
            HumanMessage(
                content=(
                    f"Target Role: {role_title}\n"
                    f"Company: {company_name}\n"
                    f"Contact Name: {contact_name}\n"
                    f"Contact Role: {contact_role}\n"
                    f"Message Type: {message_type}\n\n"
                    f"Job Description:\n{job_description}"
                )
            )
        ]

    def process_response(self, response: AIMessage, state: dict) -> dict:
        content = response.content.strip()
        # Remove any wrapping quotes the LLM might add
        content = re.sub(r'^["\']|["\']$', "", content).strip()
        return {"content": content}
