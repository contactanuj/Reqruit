"""
JoiningPrepService — deterministic, locale-specific joining preparation checklists.

These are factual, templated checklists (not LLM-generated) because accuracy
matters for legal/compliance items like I-9 deadlines and PF transfer rules.
"""

from src.db.documents.onboarding_plan import JoiningPrepItem


class JoiningPrepService:
    """Provides locale-specific joining preparation checklists."""

    def get_joining_prep(self, locale: str) -> list[JoiningPrepItem]:
        """Route to locale-specific prep based on country code."""
        locale = locale.upper().strip()
        if locale == "IN":
            return self.get_india_prep()
        if locale == "US":
            return self.get_us_prep()
        return []

    def get_india_prep(self) -> list[JoiningPrepItem]:
        """India-specific joining preparation items."""
        return [
            JoiningPrepItem(
                category="PF Transfer",
                title="PF Transfer Guidance",
                description="Transfer your Provident Fund from previous employer to new one.",
                checklist=[
                    "Link UAN (Universal Account Number) to new employer",
                    "Decide: EPF withdrawal vs transfer (transfer if <5 years service to avoid tax)",
                    "Initiate online transfer via EPFO portal",
                    "Timeline: initiate within first 2 weeks of joining",
                ],
            ),
            JoiningPrepItem(
                category="BGV",
                title="Background Verification Readiness",
                description="Keep documents ready for Background Verification process.",
                checklist=[
                    "Aadhaar card (original + copy)",
                    "PAN card",
                    "Educational certificates (all degrees and marksheets)",
                    "Previous employment proof (offer letters, experience certificates)",
                    "Relieving letters from all previous employers",
                    "Address proof (utility bill or bank statement)",
                    "Criminal background check consent form",
                ],
            ),
            JoiningPrepItem(
                category="Joining Documentation",
                title="Joining Documentation Prep",
                description="Gather all documents needed for Day 1 joining formalities.",
                checklist=[
                    "Offer letter (signed copy)",
                    "Relieving letter from previous employer",
                    "Last 3 months pay slips",
                    "Form 16 / Tax computation sheet",
                    "ID proofs (Aadhaar, PAN, passport)",
                    "Cancelled cheque / bank account details for salary credit",
                    "Passport-size photographs",
                ],
            ),
        ]

    def get_us_prep(self) -> list[JoiningPrepItem]:
        """US-specific joining preparation items."""
        return [
            JoiningPrepItem(
                category="I-9 Verification",
                title="I-9 Employment Eligibility Verification",
                description="Complete Form I-9 within 3 business days of start date.",
                checklist=[
                    "List A documents (passport, permanent resident card) OR List B + List C combination",
                    "Must complete within 3 business days of start date",
                    "E-Verify process overview with employer",
                ],
            ),
            JoiningPrepItem(
                category="Benefits Enrollment",
                title="Benefits Enrollment",
                description="Enroll in employer benefits within the enrollment window.",
                checklist=[
                    "Enrollment window: typically 30 days from start date",
                    "Health insurance: compare HMO vs PPO options",
                    "Dental and vision enrollment",
                    "Life insurance and disability options",
                ],
            ),
            JoiningPrepItem(
                category="401k Rollover",
                title="401k Rollover Considerations",
                description="Evaluate rollover options from previous employer retirement plan.",
                checklist=[
                    "Options: rollover from previous employer, direct vs indirect rollover",
                    "Tax implications of each option",
                    "Vesting schedule awareness for new employer match",
                ],
            ),
            JoiningPrepItem(
                category="FSA/HSA Setup",
                title="FSA/HSA Setup",
                description="Set up tax-advantaged health spending accounts.",
                checklist=[
                    "HSA eligibility (requires HDHP — High Deductible Health Plan)",
                    "FSA use-it-or-lose-it rules",
                    "Contribution limits for current year",
                    "Pre-tax advantage calculation",
                ],
            ),
        ]
