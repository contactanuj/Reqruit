"""
Cover letter agents — RequirementsAnalyst and CoverLetterWriter.

These two agents form the core of the cover letter workflow. They demonstrate
how BaseAgent subclasses work: each defines a system prompt, a task type
(which determines the model from the routing table), and the two abstract
methods (build_messages and process_response).

The agents are intentionally stateless — all data flows through the LangGraph
state dict. This means the same agent instance can handle multiple concurrent
workflows without interference.

Agent details
-------------
RequirementsAnalyst:
    Task type: DATA_EXTRACTION (GPT-4o-mini, temperature=0.0)
    Purpose: Extract key requirements, skills, and qualifications from a job
    description into a structured analysis. Deterministic temperature because
    extraction should be consistent — the same JD should always produce the
    same requirements list.

CoverLetterWriter:
    Task type: COVER_LETTER (Claude Sonnet, temperature=0.7)
    Purpose: Write a tailored cover letter matching the user's resume to the
    extracted requirements. Higher temperature for natural, varied writing.
    Handles the revision loop — when feedback is present, it incorporates
    the feedback and previous draft into its prompt.
"""

from langchain_core.messages import BaseMessage, HumanMessage

from src.agents.base import BaseAgent
from src.llm.models import TaskType

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------
# Kept as module-level constants so they're visible at a glance and easy to
# tune without digging into class definitions.

REQUIREMENTS_ANALYST_PROMPT = """\
You are a job requirements analyst. Given a job description, extract and \
organize the key information that a cover letter should address.

Provide a structured analysis covering:
1. **Required skills and technologies** — hard skills explicitly mentioned.
2. **Desired qualifications** — education, certifications, years of experience.
3. **Key responsibilities** — what the role actually involves day-to-day.
4. **Company values and culture signals** — any clues about what they value.
5. **Keywords to mirror** — specific terms the applicant should echo.

Be thorough but concise. Focus on what matters for writing a compelling cover \
letter, not on restating the entire job posting.\
"""

COVER_LETTER_WRITER_PROMPT = """\
You are a professional cover letter writer. Write a compelling, tailored cover \
letter that connects the applicant's experience to the job requirements.

Guidelines:
- Open with a strong hook that shows genuine interest in the specific role.
- Match the applicant's skills and experience to the key requirements.
- Use specific examples from their resume — avoid vague claims.
- Mirror keywords from the job description naturally.
- Keep it concise — 3-4 paragraphs, under 400 words.
- Professional but personable tone — not robotic or overly formal.
- Close with a clear call to action.

If revision feedback is provided, incorporate it while maintaining the letter's \
overall quality and coherence. Address every point in the feedback.\
"""


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------


class RequirementsAnalyst(BaseAgent):
    """
    Extracts structured requirements from a job description.

    Reads the job_description from state and returns a requirements_analysis
    string that the CoverLetterWriter uses to align the cover letter with
    the job's needs.
    """

    def __init__(self) -> None:
        super().__init__(
            name="requirements_analyst",
            task_type=TaskType.DATA_EXTRACTION,
            system_prompt=REQUIREMENTS_ANALYST_PROMPT,
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        job_description = state.get("job_description", "")
        return [
            HumanMessage(
                content=(
                    "Analyze the following job description and extract the "
                    "key requirements:\n\n"
                    f"{job_description}"
                )
            )
        ]

    def process_response(self, response, state: dict) -> dict:
        return {"requirements_analysis": response.content}


class CoverLetterWriter(BaseAgent):
    """
    Writes a tailored cover letter from requirements and resume.

    Reads requirements_analysis and resume_text from state. When feedback
    is present (revision loop), also includes the previous cover_letter draft
    and the user's feedback so the model can refine its output.
    """

    def __init__(self) -> None:
        super().__init__(
            name="cover_letter_writer",
            task_type=TaskType.COVER_LETTER,
            system_prompt=COVER_LETTER_WRITER_PROMPT,
        )

    def build_messages(self, state: dict) -> list[BaseMessage]:
        requirements = state.get("requirements_analysis", "")
        resume = state.get("resume_text", "")
        memory_context = state.get("memory_context", "")
        feedback = state.get("feedback", "")
        previous_draft = state.get("cover_letter", "")

        parts = [
            "## Requirements Analysis\n",
            requirements,
            "\n\n## Applicant Resume\n",
            resume,
        ]

        # Include memory context (past cover letters, relevant resume chunks)
        # when available. This gives the writer examples and context from
        # past interactions to produce better-tailored output.
        if memory_context:
            parts.extend(["\n\n", memory_context])

        # Revision loop — include the previous draft and feedback so the
        # model knows what to improve rather than starting from scratch.
        if feedback and previous_draft:
            parts.extend([
                "\n\n## Previous Draft\n",
                previous_draft,
                "\n\n## Revision Feedback\n",
                feedback,
                "\n\nPlease revise the cover letter addressing the feedback above.",
            ])
        else:
            parts.append(
                "\n\nWrite a tailored cover letter for this applicant."
            )

        return [HumanMessage(content="".join(parts))]

    def process_response(self, response, state: dict) -> dict:
        return {"cover_letter": response.content}
