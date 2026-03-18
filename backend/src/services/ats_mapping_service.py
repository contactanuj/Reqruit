"""
ATS mapping service — transforms generic profile export to platform-specific formats.

Maps the generic ATS export (from ATSExportService) to field names expected by
specific ATS platforms: Greenhouse, Lever, Workday, and a generic fallback.

Each platform mapping defines how our canonical fields translate to the
platform's expected field names and structure.
"""

import structlog

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Platform field mappings
# ---------------------------------------------------------------------------

PLATFORM_MAPPINGS: dict[str, dict[str, str]] = {
    "greenhouse": {
        "name": "candidate_name",
        "email": "email_address",
        "phone": "phone_number",
        "location": "location",
        "linkedin": "social_url",
        "company": "employer",
        "title": "job_title",
        "institution": "school_name",
        "degree": "degree_type",
        "field_of_study": "discipline",
    },
    "lever": {
        "name": "name",
        "email": "email",
        "phone": "phone",
        "location": "location",
        "linkedin": "links",
        "company": "org",
        "title": "title",
        "institution": "school",
        "degree": "degree",
        "field_of_study": "field",
    },
    "workday": {
        "name": "legalName",
        "email": "emailAddress",
        "phone": "phoneNumber",
        "location": "addressLine1",
        "linkedin": "linkedInProfile",
        "company": "companyName",
        "title": "positionTitle",
        "institution": "universityName",
        "degree": "degreeReceived",
        "field_of_study": "majorDescription",
    },
}


def get_supported_platforms() -> list[str]:
    """Return list of supported ATS platform names."""
    return sorted(PLATFORM_MAPPINGS.keys())


def map_to_platform(export_data: dict, platform: str) -> dict:
    """
    Transform a generic ATS export to a platform-specific format.

    Args:
        export_data: Output from ATSExportService.export_profile().
        platform: Target ATS platform name (greenhouse, lever, workday).

    Returns:
        Platform-specific dict with mapped field names.
        Falls back to generic format if platform is unknown.
    """
    mapping = PLATFORM_MAPPINGS.get(platform)
    if mapping is None:
        logger.info("ats_mapping_fallback", platform=platform)
        return export_data

    personal = export_data.get("personal_info", {})
    mapped_personal = {}
    for generic_key, platform_key in mapping.items():
        if generic_key in personal:
            mapped_personal[platform_key] = personal[generic_key]

    mapped_experience = [
        {
            mapping.get("company", "company"): exp.get("company", ""),
            mapping.get("title", "title"): exp.get("title", ""),
            "start_date": exp.get("start_date", ""),
            "end_date": exp.get("end_date", ""),
            "highlights": exp.get("highlights", []),
        }
        for exp in export_data.get("work_experience", [])
    ]

    mapped_education = [
        {
            mapping.get("institution", "institution"): edu.get("institution", ""),
            mapping.get("degree", "degree"): edu.get("degree", ""),
            mapping.get("field_of_study", "field_of_study"): edu.get("field_of_study", ""),
            "start_date": edu.get("start_date", ""),
            "end_date": edu.get("end_date", ""),
        }
        for edu in export_data.get("education", [])
    ]

    return {
        "platform": platform,
        "format_version": export_data.get("format_version", "1.0"),
        "personal_info": mapped_personal,
        "work_experience": mapped_experience,
        "education": mapped_education,
        "skills": export_data.get("skills", []),
        "target_roles": export_data.get("target_roles", []),
    }
