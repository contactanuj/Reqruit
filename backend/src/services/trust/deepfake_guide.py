"""
DeepfakeInterviewGuide — static checklist for detecting deepfake video interviews.

Pure data resource — no LLM calls, no external API calls.
"""

from src.services.trust.models import ChecklistCategory, ChecklistItem, DeepfakeChecklist


class DeepfakeInterviewGuide:
    """Returns a structured deepfake detection checklist."""

    @staticmethod
    def get_guide() -> DeepfakeChecklist:
        return DeepfakeChecklist(
            categories=[
                ChecklistCategory(
                    category_name="Audio-Visual Sync Checks",
                    items=[
                        ChecklistItem(
                            check="Lip sync mismatch",
                            description="Watch for delays between lip movement and audio",
                            severity="critical",
                        ),
                        ChecklistItem(
                            check="Unnatural facial movements",
                            description="Look for jittery or flickering around jawline and eyes",
                            severity="critical",
                        ),
                        ChecklistItem(
                            check="Audio quality inconsistency",
                            description="Voice quality changes when interviewer turns head",
                            severity="important",
                        ),
                        ChecklistItem(
                            check="Robotic speech patterns",
                            description="Unusually flat intonation or mechanical cadence",
                            severity="important",
                        ),
                    ],
                ),
                ChecklistCategory(
                    category_name="Background Consistency Indicators",
                    items=[
                        ChecklistItem(
                            check="Static background",
                            description="Background that never changes even with head movement",
                            severity="important",
                        ),
                        ChecklistItem(
                            check="Edge artifacts",
                            description="Blurring or pixelation around hair and face edges",
                            severity="critical",
                        ),
                        ChecklistItem(
                            check="Lighting inconsistency",
                            description="Face lighting doesn't match room lighting direction",
                            severity="important",
                        ),
                        ChecklistItem(
                            check="Virtual background glitches",
                            description="Intermittent body part disappearance at edges",
                            severity="informational",
                        ),
                    ],
                ),
                ChecklistCategory(
                    category_name="Identity Verification Prompts",
                    items=[
                        ChecklistItem(
                            check="Ask to show company ID badge",
                            description="Request visual confirmation of employment",
                            severity="critical",
                        ),
                        ChecklistItem(
                            check="Request hand wave near face",
                            description="Deepfakes often glitch with hand-face occlusion",
                            severity="critical",
                        ),
                        ChecklistItem(
                            check="Ask to turn profile view",
                            description="Side profiles are harder to deepfake convincingly",
                            severity="important",
                        ),
                        ChecklistItem(
                            check="Verify via company email",
                            description="Ask interviewer to send a follow-up from company domain",
                            severity="critical",
                        ),
                        ChecklistItem(
                            check="Cross-reference LinkedIn",
                            description="Check interviewer's LinkedIn matches stated identity",
                            severity="important",
                        ),
                    ],
                ),
                ChecklistCategory(
                    category_name="Red Flag Indicators",
                    items=[
                        ChecklistItem(
                            check="Interviewer refuses video",
                            description="Claims technical issues but can hear you fine",
                            severity="critical",
                        ),
                        ChecklistItem(
                            check="No company email provided",
                            description="Uses personal email for official communication",
                            severity="important",
                        ),
                        ChecklistItem(
                            check="Unusually short interview",
                            description="Rushes to offer without proper assessment",
                            severity="important",
                        ),
                        ChecklistItem(
                            check="Requests sensitive information during interview",
                            description="Asks for SSN/Aadhaar/bank details",
                            severity="critical",
                        ),
                        ChecklistItem(
                            check="Interview not on standard platform",
                            description="Uses obscure video tool instead of Zoom/Teams/Meet",
                            severity="informational",
                        ),
                    ],
                ),
            ],
            last_updated="2026-03-16",
        )
