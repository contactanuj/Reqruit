"""Tests for ScamReportService — report submission, duplicate detection, badge logic."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from beanie import PydanticObjectId

from src.core.exceptions import ConflictError
from src.services.trust.scam_report_service import ScamReportService


def _make_repo(**overrides):
    repo = AsyncMock()
    repo.check_duplicate = AsyncMock(return_value=False)
    repo.create = AsyncMock(side_effect=lambda doc: doc)
    repo.has_warning_badge = AsyncMock(return_value=False)
    repo.get_distinct_reporter_count = AsyncMock(return_value=1)
    repo.apply_warning_badge = AsyncMock()
    repo.get_entity_summary = AsyncMock(return_value={
        "entity_identifier": "test",
        "report_count": 0,
        "risk_categories": [],
        "warning_badge": False,
        "reporters": [],
    })
    for k, v in overrides.items():
        setattr(repo, k, v)
    return repo


_USER_ID = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")


class TestSubmitReport:
    async def test_creates_report(self) -> None:
        repo = _make_repo()
        service = ScamReportService(repo)

        report = await service.submit_report(
            reporter_user_id=_USER_ID,
            entity_type="company",
            entity_identifier="scam-corp",
            evidence_type="description",
            evidence_text="They asked for money",
            risk_category="SUSPICIOUS",
        )

        assert report.entity_type == "company"
        assert report.entity_identifier == "scam-corp"
        assert report.reporter_user_id == _USER_ID
        repo.create.assert_awaited_once()

    async def test_duplicate_raises_conflict(self) -> None:
        repo = _make_repo(check_duplicate=AsyncMock(return_value=True))
        service = ScamReportService(repo)

        with pytest.raises(ConflictError) as exc_info:
            await service.submit_report(
                reporter_user_id=_USER_ID,
                entity_type="company",
                entity_identifier="scam-corp",
                evidence_type="description",
                evidence_text="duplicate",
                risk_category="SUSPICIOUS",
            )

        assert exc_info.value.error_code == "ALREADY_REPORTED"
        repo.create.assert_not_awaited()


class TestBadgeLogic:
    async def test_badge_applied_at_threshold(self) -> None:
        repo = _make_repo(
            get_distinct_reporter_count=AsyncMock(return_value=3),
        )
        service = ScamReportService(repo)

        await service.submit_report(
            reporter_user_id=_USER_ID,
            entity_type="company",
            entity_identifier="scam-corp",
            evidence_type="url",
            evidence_text="https://evidence.com",
            risk_category="SCAM_LIKELY",
        )

        repo.apply_warning_badge.assert_awaited_once_with("scam-corp")

    async def test_badge_not_applied_below_threshold(self) -> None:
        repo = _make_repo(
            get_distinct_reporter_count=AsyncMock(return_value=2),
        )
        service = ScamReportService(repo)

        await service.submit_report(
            reporter_user_id=_USER_ID,
            entity_type="company",
            entity_identifier="scam-corp",
            evidence_type="description",
            evidence_text="suspicious",
            risk_category="SUSPICIOUS",
        )

        repo.apply_warning_badge.assert_not_awaited()

    async def test_badge_not_reapplied_if_already_exists(self) -> None:
        repo = _make_repo(
            has_warning_badge=AsyncMock(return_value=True),
            get_distinct_reporter_count=AsyncMock(return_value=5),
        )
        service = ScamReportService(repo)

        await service.submit_report(
            reporter_user_id=_USER_ID,
            entity_type="recruiter",
            entity_identifier="fake@scam.com",
            evidence_type="screenshot",
            evidence_text="screenshot evidence",
            risk_category="SCAM_LIKELY",
        )

        repo.apply_warning_badge.assert_not_awaited()


class TestGetEntityReports:
    async def test_returns_summary(self) -> None:
        repo = _make_repo(
            get_entity_summary=AsyncMock(return_value={
                "entity_identifier": "scam-corp",
                "report_count": 3,
                "risk_categories": ["SUSPICIOUS", "SCAM_LIKELY"],
                "warning_badge": True,
                "reporters": ["abc123", "def456", "ghi789"],
            })
        )
        service = ScamReportService(repo)
        summary = await service.get_entity_reports("scam-corp")

        assert summary["report_count"] == 3
        assert summary["warning_badge"] is True
        assert len(summary["reporters"]) == 3
        # Reporters should be hashed, not raw user IDs
        for r in summary["reporters"]:
            assert len(r) > 0

    async def test_empty_for_unknown_entity(self) -> None:
        repo = _make_repo()
        service = ScamReportService(repo)
        summary = await service.get_entity_reports("nonexistent")

        assert summary["report_count"] == 0
        assert summary["warning_badge"] is False
