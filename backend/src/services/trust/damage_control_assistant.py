"""
DamageControlAssistant — generates step-by-step recovery plans for scam victims.

Rule-based service with jurisdiction-specific templates for India and US.
All government/agency URLs are hardcoded for accuracy.
"""

from src.services.trust.models import RecoveryPlan, RecoveryStep

_VALID_SCAM_TYPES = {"financial_fraud", "identity_theft", "fake_offer", "data_breach"}
_VALID_JURISDICTIONS = {"IN", "US"}


class DamageControlAssistant:
    """Generates jurisdiction-specific recovery plans for scam victims."""

    def generate_plan(
        self,
        scam_type: str,
        information_shared: list[str],
        jurisdiction: str,
        additional_context: str = "",
    ) -> RecoveryPlan:
        """Build a complete recovery plan based on scam type and jurisdiction."""
        immediate = self._common_immediate_actions(scam_type, information_shared)

        if jurisdiction == "IN":
            complaints = self._india_complaint_steps(scam_type, information_shared)
        else:
            complaints = self._us_complaint_steps(scam_type, information_shared)

        monitoring = self._monitoring_steps(jurisdiction, information_shared)
        flagging = self._platform_flagging_steps(jurisdiction)
        recommendations = self._additional_recommendations(scam_type)

        return RecoveryPlan(
            scam_type=scam_type,
            jurisdiction=jurisdiction,
            immediate_actions=immediate,
            complaint_filing=complaints,
            monitoring_steps=monitoring,
            platform_flagging=flagging,
            additional_recommendations=recommendations,
        )

    @staticmethod
    def _common_immediate_actions(
        scam_type: str, information_shared: list[str]
    ) -> list[RecoveryStep]:
        step = 0
        actions: list[RecoveryStep] = []

        step += 1
        actions.append(RecoveryStep(
            step_number=step,
            action="Change all passwords",
            details="Immediately change passwords for all accounts using the shared email address. Use unique, strong passwords for each account.",
            urgency="immediate",
        ))

        step += 1
        actions.append(RecoveryStep(
            step_number=step,
            action="Enable two-factor authentication",
            details="Enable 2FA on all financial accounts, email, and social media accounts.",
            urgency="immediate",
        ))

        if scam_type == "financial_fraud" or "bank_details" in information_shared:
            step += 1
            actions.append(RecoveryStep(
                step_number=step,
                action="Freeze bank accounts and cards",
                details="Contact your bank immediately to freeze compromised accounts and request new cards.",
                urgency="immediate",
            ))

        step += 1
        actions.append(RecoveryStep(
            step_number=step,
            action="Preserve evidence",
            details="Screenshot and save all scam communication — emails, messages, call logs, and transaction records.",
            urgency="immediate",
        ))

        step += 1
        actions.append(RecoveryStep(
            step_number=step,
            action="Block the scammer",
            details="Block the scammer's phone number, email address, and social media accounts.",
            urgency="immediate",
        ))

        return actions

    @staticmethod
    def _india_complaint_steps(
        scam_type: str, information_shared: list[str]
    ) -> list[RecoveryStep]:
        step = 0
        steps: list[RecoveryStep] = []

        step += 1
        steps.append(RecoveryStep(
            step_number=step,
            action="File complaint on cybercrime.gov.in",
            details="Visit the National Cyber Crime Reporting Portal. Select the appropriate category, provide evidence, and note the complaint number.",
            urgency="within_24h",
            url="https://cybercrime.gov.in",
        ))

        step += 1
        steps.append(RecoveryStep(
            step_number=step,
            action="Contact local cyber cell",
            details="Visit your nearest cyber crime police station to file an FIR. Bring screenshots and evidence. Find your nearest cyber cell via the state police website.",
            urgency="within_24h",
        ))

        if scam_type == "financial_fraud":
            step += 1
            steps.append(RecoveryStep(
                step_number=step,
                action="File RBI complaint",
                details="Report financial fraud to the Reserve Bank of India through the Complaint Management System.",
                urgency="within_24h",
                url="https://cms.rbi.org.in",
            ))

        if "aadhaar" in information_shared:
            step += 1
            steps.append(RecoveryStep(
                step_number=step,
                action="Lock Aadhaar biometrics",
                details="Lock your Aadhaar biometrics immediately via the myAadhaar portal. Also enable virtual ID to prevent misuse of your Aadhaar number.",
                urgency="immediate",
                url="https://myaadhaar.uidai.gov.in",
            ))

        if "pan" in information_shared:
            step += 1
            steps.append(RecoveryStep(
                step_number=step,
                action="Report PAN misuse to Income Tax department",
                details="File a complaint with the Income Tax department about potential PAN misuse. Monitor Form 26AS for unauthorized transactions.",
                urgency="within_24h",
                url="https://www.incometax.gov.in",
            ))

        return steps

    @staticmethod
    def _us_complaint_steps(
        scam_type: str, information_shared: list[str]
    ) -> list[RecoveryStep]:
        step = 0
        steps: list[RecoveryStep] = []

        step += 1
        steps.append(RecoveryStep(
            step_number=step,
            action="Report to FTC at IdentityTheft.gov",
            details="File an identity theft report with the FTC. This creates a personalized recovery plan and pre-filled letters for creditors.",
            urgency="within_24h",
            url="https://identitytheft.gov",
        ))

        step += 1
        steps.append(RecoveryStep(
            step_number=step,
            action="File IC3 complaint",
            details="Report the internet crime to the FBI's Internet Crime Complaint Center.",
            urgency="within_24h",
            url="https://www.ic3.gov",
        ))

        step += 1
        steps.append(RecoveryStep(
            step_number=step,
            action="Freeze credit with Equifax",
            details="Place a security freeze on your credit report with Equifax.",
            urgency="within_24h",
            url="https://www.equifax.com/personal/credit-report-services/credit-freeze/",
        ))

        step += 1
        steps.append(RecoveryStep(
            step_number=step,
            action="Freeze credit with Experian",
            details="Place a security freeze on your credit report with Experian.",
            urgency="within_24h",
            url="https://www.experian.com/freeze/center.html",
        ))

        step += 1
        steps.append(RecoveryStep(
            step_number=step,
            action="Freeze credit with TransUnion",
            details="Place a security freeze on your credit report with TransUnion.",
            urgency="within_24h",
            url="https://www.transunion.com/credit-freeze",
        ))

        if "ssn" in information_shared:
            step += 1
            steps.append(RecoveryStep(
                step_number=step,
                action="Contact Social Security Administration",
                details="Report SSN compromise to the SSA. Consider requesting a new SSN if identity theft is severe.",
                urgency="within_24h",
                url="https://www.ssa.gov",
            ))

            step += 1
            steps.append(RecoveryStep(
                step_number=step,
                action="Get IRS Identity Protection PIN",
                details="Apply for an IP PIN from the IRS to prevent fraudulent tax returns filed using your SSN.",
                urgency="within_week",
                url="https://www.irs.gov/identity-theft-fraud-scams/get-an-identity-protection-pin",
            ))

        step += 1
        steps.append(RecoveryStep(
            step_number=step,
            action="Check state data breach notification rights",
            details="Review your state Attorney General's website for data breach notification rights and additional state-specific protections.",
            urgency="within_week",
        ))

        return steps

    @staticmethod
    def _monitoring_steps(
        jurisdiction: str, information_shared: list[str]
    ) -> list[RecoveryStep]:
        steps: list[RecoveryStep] = []
        step = 0

        step += 1
        steps.append(RecoveryStep(
            step_number=step,
            action="Set up credit monitoring",
            details="Enroll in a credit monitoring service to receive alerts on new accounts or inquiries."
            + (" Check CIBIL score regularly." if jurisdiction == "IN" else " Use annualcreditreport.com for free reports."),
            urgency="within_24h",
        ))

        step += 1
        steps.append(RecoveryStep(
            step_number=step,
            action="Monitor bank statements",
            details="Review all bank and credit card statements weekly for unauthorized transactions for at least 6 months.",
            urgency="ongoing",
        ))

        if "email" in information_shared:
            step += 1
            steps.append(RecoveryStep(
                step_number=step,
                action="Check email breach exposure",
                details="Use haveibeenpwned.com to check if your email appears in known data breaches.",
                urgency="within_24h",
                url="https://haveibeenpwned.com",
            ))

        return steps

    @staticmethod
    def _platform_flagging_steps(jurisdiction: str) -> list[RecoveryStep]:
        steps: list[RecoveryStep] = []
        step = 0

        step += 1
        steps.append(RecoveryStep(
            step_number=step,
            action="Report on LinkedIn",
            details="Report the scammer's profile and job posting on LinkedIn using the 'Report' option.",
            urgency="within_24h",
        ))

        if jurisdiction == "IN":
            step += 1
            steps.append(RecoveryStep(
                step_number=step,
                action="Report on Naukri",
                details="Report the fraudulent job listing on Naukri.com through their grievance reporting system.",
                urgency="within_24h",
            ))
        else:
            step += 1
            steps.append(RecoveryStep(
                step_number=step,
                action="Report on Indeed",
                details="Report the fraudulent job listing on Indeed through their 'Report Job' feature.",
                urgency="within_24h",
            ))

        return steps

    @staticmethod
    def _additional_recommendations(scam_type: str) -> list[str]:
        recs = [
            "Keep copies of all filed complaints and reference numbers",
            "Do not engage further with the scammer even if they contact you again",
        ]
        if scam_type == "financial_fraud":
            recs.append("Consult a financial advisor about additional protective measures")
        if scam_type == "identity_theft":
            recs.append("Consider placing a fraud alert with credit bureaus (lasts 1 year, renewable)")
        if scam_type == "fake_offer":
            recs.append("Verify future job offers through the company's official website and HR department")
        return recs
