"""Tests for ATS mapping service — platform-specific field mapping."""

from src.services.ats_mapping_service import (
    get_supported_platforms,
    map_to_platform,
)


def _make_export_data():
    return {
        "format_version": "1.0",
        "personal_info": {
            "name": "Alice Smith",
            "email": "alice@example.com",
            "phone": "+1-555-0100",
            "location": "San Francisco",
            "linkedin": "linkedin.com/in/alice",
        },
        "work_experience": [
            {
                "company": "Acme Corp",
                "title": "Senior Engineer",
                "start_date": "2022-01",
                "end_date": "2024-03",
                "highlights": ["Built API"],
            },
        ],
        "education": [
            {
                "institution": "MIT",
                "degree": "B.S.",
                "field_of_study": "CS",
                "start_date": "2018",
                "end_date": "2022",
            },
        ],
        "skills": ["Python", "Go"],
        "target_roles": ["Backend Engineer"],
    }


class TestGetSupportedPlatforms:
    def test_returns_sorted_list(self):
        platforms = get_supported_platforms()
        assert "greenhouse" in platforms
        assert "lever" in platforms
        assert "workday" in platforms
        assert platforms == sorted(platforms)


class TestMapToPlatform:
    def test_greenhouse_mapping(self):
        data = _make_export_data()
        result = map_to_platform(data, "greenhouse")

        assert result["platform"] == "greenhouse"
        assert result["personal_info"]["candidate_name"] == "Alice Smith"
        assert result["personal_info"]["email_address"] == "alice@example.com"
        assert result["work_experience"][0]["employer"] == "Acme Corp"
        assert result["work_experience"][0]["job_title"] == "Senior Engineer"
        assert result["education"][0]["school_name"] == "MIT"
        assert result["education"][0]["degree_type"] == "B.S."

    def test_lever_mapping(self):
        data = _make_export_data()
        result = map_to_platform(data, "lever")

        assert result["platform"] == "lever"
        assert result["personal_info"]["name"] == "Alice Smith"
        assert result["personal_info"]["email"] == "alice@example.com"
        assert result["work_experience"][0]["org"] == "Acme Corp"
        assert result["education"][0]["school"] == "MIT"

    def test_workday_mapping(self):
        data = _make_export_data()
        result = map_to_platform(data, "workday")

        assert result["platform"] == "workday"
        assert result["personal_info"]["legalName"] == "Alice Smith"
        assert result["personal_info"]["emailAddress"] == "alice@example.com"
        assert result["work_experience"][0]["companyName"] == "Acme Corp"
        assert result["education"][0]["universityName"] == "MIT"

    def test_unknown_platform_returns_generic(self):
        data = _make_export_data()
        result = map_to_platform(data, "unknown_ats")

        # Should return original data unchanged
        assert result == data

    def test_preserves_skills_and_roles(self):
        data = _make_export_data()
        result = map_to_platform(data, "greenhouse")

        assert result["skills"] == ["Python", "Go"]
        assert result["target_roles"] == ["Backend Engineer"]

    def test_empty_export_data(self):
        data = {
            "format_version": "1.0",
            "personal_info": {},
            "work_experience": [],
            "education": [],
            "skills": [],
            "target_roles": [],
        }
        result = map_to_platform(data, "greenhouse")

        assert result["platform"] == "greenhouse"
        assert result["personal_info"] == {}
        assert result["work_experience"] == []
        assert result["education"] == []

    def test_preserves_dates_and_highlights(self):
        data = _make_export_data()
        result = map_to_platform(data, "lever")

        exp = result["work_experience"][0]
        assert exp["start_date"] == "2022-01"
        assert exp["end_date"] == "2024-03"
        assert exp["highlights"] == ["Built API"]
