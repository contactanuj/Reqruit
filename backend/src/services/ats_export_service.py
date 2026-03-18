"""
ATS export service — assembles profile + resume data for auto-fill.

Generates a structured payload compatible with common ATS fields:
- Personal info (name, email, phone, location)
- Work experience (company, title, dates, highlights)
- Education (institution, degree, field, dates)
- Skills (list of string tags)
- Summary / objective

This data can be consumed by browser extensions or API integrations
to auto-fill application forms on job boards and company ATS portals.
"""

import structlog

from src.repositories.profile_repository import ProfileRepository
from src.repositories.resume_repository import ResumeRepository

logger = structlog.get_logger()


class ATSExportService:
    """Assembles profile and resume data into ATS-compatible export format."""

    def __init__(
        self,
        profile_repo: ProfileRepository,
        resume_repo: ResumeRepository,
    ) -> None:
        self._profile_repo = profile_repo
        self._resume_repo = resume_repo

    async def export_profile(self, user_id) -> dict:
        """
        Build an ATS-compatible profile export for the given user.

        Merges data from Profile (skills, target_roles, preferences) and
        the master Resume (parsed contact info, work experience, education).

        Returns:
            Structured dict with personal_info, work_experience, education,
            skills, and preferences sections.
        """
        profile = await self._profile_repo.find_one({"user_id": user_id})
        resume = await self._resume_repo.get_master_resume(user_id)

        personal_info = {}
        work_experience = []
        education = []
        raw_skills = []

        if resume and resume.parsed_data:
            parsed = resume.parsed_data
            if parsed.contact_info:
                ci = parsed.contact_info
                personal_info = {
                    "name": ci.name or "",
                    "email": ci.email or "",
                    "phone": ci.phone or "",
                    "location": ci.location or "",
                    "linkedin": ci.linkedin or "",
                }
            work_experience = [
                {
                    "company": exp.company,
                    "title": exp.title,
                    "start_date": exp.start_date or "",
                    "end_date": exp.end_date or "",
                    "highlights": exp.highlights,
                }
                for exp in parsed.work_experience
            ]
            education = [
                {
                    "institution": edu.institution,
                    "degree": edu.degree,
                    "field_of_study": edu.field_of_study,
                    "start_date": edu.start_date or "",
                    "end_date": edu.end_date or "",
                }
                for edu in parsed.education
            ]
            raw_skills = list(parsed.skills)

        # Merge skills from profile and resume (deduplicated)
        profile_skills = profile.skills if profile else []
        all_skills = list(dict.fromkeys(raw_skills + profile_skills))

        preferences = {}
        target_roles = []
        if profile:
            target_roles = profile.target_roles
            if profile.preferences:
                preferences = {
                    "remote_preference": str(profile.preferences.remote_preference),
                    "preferred_locations": profile.preferences.preferred_locations,
                }

        return {
            "format_version": "1.0",
            "personal_info": personal_info,
            "work_experience": work_experience,
            "education": education,
            "skills": all_skills,
            "target_roles": target_roles,
            "preferences": preferences,
        }
