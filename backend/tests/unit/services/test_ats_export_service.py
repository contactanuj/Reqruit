"""Tests for ATSExportService — profile data export for ATS auto-fill."""

from unittest.mock import AsyncMock, MagicMock

from src.services.ats_export_service import ATSExportService


def _make_contact_info(**overrides):
    defaults = {
        "name": "Alice Smith",
        "email": "alice@example.com",
        "phone": "+1-555-0100",
        "location": "San Francisco, CA",
        "linkedin": "linkedin.com/in/alice",
    }
    defaults.update(overrides)
    ci = MagicMock()
    for k, v in defaults.items():
        setattr(ci, k, v)
    return ci


def _make_work_exp(**overrides):
    defaults = {
        "company": "Acme Corp",
        "title": "Senior Engineer",
        "start_date": "2022-01",
        "end_date": "2024-03",
        "highlights": ["Built API", "Led team of 5"],
    }
    defaults.update(overrides)
    exp = MagicMock()
    for k, v in defaults.items():
        setattr(exp, k, v)
    return exp


def _make_education(**overrides):
    defaults = {
        "institution": "MIT",
        "degree": "B.S.",
        "field_of_study": "Computer Science",
        "start_date": "2018",
        "end_date": "2022",
    }
    defaults.update(overrides)
    edu = MagicMock()
    for k, v in defaults.items():
        setattr(edu, k, v)
    return edu


def _make_parsed_data(contact=None, experience=None, education=None, skills=None):
    parsed = MagicMock()
    parsed.contact_info = contact or _make_contact_info()
    parsed.work_experience = experience or [_make_work_exp()]
    parsed.education = education or [_make_education()]
    parsed.skills = skills or ["Python", "FastAPI"]
    return parsed


def _make_resume(parsed_data=None):
    resume = MagicMock()
    resume.parsed_data = parsed_data or _make_parsed_data()
    return resume


def _make_profile(**overrides):
    defaults = {
        "skills": ["MongoDB", "Docker"],
        "target_roles": ["Backend Engineer", "SRE"],
    }
    defaults.update(overrides)
    profile = MagicMock()
    for k, v in defaults.items():
        setattr(profile, k, v)
    prefs = MagicMock()
    prefs.remote_preference = "remote"
    prefs.preferred_locations = ["San Francisco"]
    profile.preferences = prefs
    return profile


class TestExportProfile:
    async def test_full_export(self):
        profile = _make_profile()
        resume = _make_resume()
        profile_repo = MagicMock()
        profile_repo.find_one = AsyncMock(return_value=profile)
        resume_repo = MagicMock()
        resume_repo.get_master_resume = AsyncMock(return_value=resume)

        service = ATSExportService(profile_repo=profile_repo, resume_repo=resume_repo)
        result = await service.export_profile("user1")

        assert result["format_version"] == "1.0"
        assert result["personal_info"]["name"] == "Alice Smith"
        assert result["personal_info"]["email"] == "alice@example.com"
        assert len(result["work_experience"]) == 1
        assert result["work_experience"][0]["company"] == "Acme Corp"
        assert len(result["education"]) == 1
        assert result["education"][0]["institution"] == "MIT"
        # Skills merged: resume ["Python", "FastAPI"] + profile ["MongoDB", "Docker"]
        assert "Python" in result["skills"]
        assert "MongoDB" in result["skills"]
        assert result["target_roles"] == ["Backend Engineer", "SRE"]
        assert result["preferences"]["remote_preference"] == "remote"

    async def test_export_without_resume(self):
        profile = _make_profile()
        profile_repo = MagicMock()
        profile_repo.find_one = AsyncMock(return_value=profile)
        resume_repo = MagicMock()
        resume_repo.get_master_resume = AsyncMock(return_value=None)

        service = ATSExportService(profile_repo=profile_repo, resume_repo=resume_repo)
        result = await service.export_profile("user1")

        assert result["personal_info"] == {}
        assert result["work_experience"] == []
        assert result["education"] == []
        # Only profile skills
        assert result["skills"] == ["MongoDB", "Docker"]

    async def test_export_without_profile(self):
        resume = _make_resume()
        profile_repo = MagicMock()
        profile_repo.find_one = AsyncMock(return_value=None)
        resume_repo = MagicMock()
        resume_repo.get_master_resume = AsyncMock(return_value=resume)

        service = ATSExportService(profile_repo=profile_repo, resume_repo=resume_repo)
        result = await service.export_profile("user1")

        assert result["personal_info"]["name"] == "Alice Smith"
        assert result["skills"] == ["Python", "FastAPI"]
        assert result["target_roles"] == []
        assert result["preferences"] == {}

    async def test_export_deduplicates_skills(self):
        profile = _make_profile(skills=["Python", "Go"])
        resume = _make_resume(_make_parsed_data(skills=["Python", "FastAPI"]))
        profile_repo = MagicMock()
        profile_repo.find_one = AsyncMock(return_value=profile)
        resume_repo = MagicMock()
        resume_repo.get_master_resume = AsyncMock(return_value=resume)

        service = ATSExportService(profile_repo=profile_repo, resume_repo=resume_repo)
        result = await service.export_profile("user1")

        # Python appears in both but should be deduplicated
        assert result["skills"].count("Python") == 1
        assert "FastAPI" in result["skills"]
        assert "Go" in result["skills"]

    async def test_export_empty_user(self):
        profile_repo = MagicMock()
        profile_repo.find_one = AsyncMock(return_value=None)
        resume_repo = MagicMock()
        resume_repo.get_master_resume = AsyncMock(return_value=None)

        service = ATSExportService(profile_repo=profile_repo, resume_repo=resume_repo)
        result = await service.export_profile("user1")

        assert result["format_version"] == "1.0"
        assert result["personal_info"] == {}
        assert result["work_experience"] == []
        assert result["education"] == []
        assert result["skills"] == []
        assert result["target_roles"] == []

    async def test_multiple_work_experiences(self):
        exps = [
            _make_work_exp(company="Acme", title="Senior"),
            _make_work_exp(company="Beta Inc", title="Junior"),
        ]
        resume = _make_resume(_make_parsed_data(experience=exps))
        profile_repo = MagicMock()
        profile_repo.find_one = AsyncMock(return_value=None)
        resume_repo = MagicMock()
        resume_repo.get_master_resume = AsyncMock(return_value=resume)

        service = ATSExportService(profile_repo=profile_repo, resume_repo=resume_repo)
        result = await service.export_profile("user1")

        assert len(result["work_experience"]) == 2
        assert result["work_experience"][0]["company"] == "Acme"
        assert result["work_experience"][1]["company"] == "Beta Inc"
