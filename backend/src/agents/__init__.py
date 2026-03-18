# Specialized AI agents (13 total across 4 workflows).
# Each agent has one focused job and can use a different LLM model.

from src.agents.base import BaseAgent
from src.agents.cover_letter import (
    CoverLetterWriter,
    RequirementsAnalyst,
)

__all__ = [
    "BaseAgent",
    "CoverLetterWriter",
    "RequirementsAnalyst",
]
