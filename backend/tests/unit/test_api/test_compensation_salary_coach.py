"""
Tests for the salary coach endpoint.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import get_current_user


def _make_user():
    user = MagicMock()
    user.id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
    user.email = "test@example.com"
    user.is_active = True
    return user


def _override(app, user):
    app.dependency_overrides[get_current_user] = lambda: user


def _mock_agent_response():
    """Returns a dict matching agent process_response output."""
    scripts = [
        {"script_text": "Script 1", "strategy_name": "anchoring_high",
         "strategy_explanation": "Sets high anchor", "risk_level": "high"},
        {"script_text": "Script 2", "strategy_name": "deflecting",
         "strategy_explanation": "Delays commitment", "risk_level": "low"},
        {"script_text": "Script 3", "strategy_name": "range_based",
         "strategy_explanation": "Shows flexibility", "risk_level": "medium"},
    ]
    return {"scripts": json.dumps(scripts), "general_tips": json.dumps(["Tip 1", "Tip 2"])}


class TestSalaryCoachEndpoint:

    async def test_200_with_scripts(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        with patch(
            "src.api.routes.compensation.compensation_coach_agent",
            new=AsyncMock(return_value=_mock_agent_response()),
        ):
            response = await client.post(
                "/compensation/salary-coach",
                json={
                    "current_ctc": 1500000,
                    "target_range_min": 2000000,
                    "target_range_max": 2500000,
                    "role_title": "SDE-2",
                    "company_name": "Acme Corp",
                    "locale": "IN",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["scripts"]) == 3
        assert data["locale_used"] == "IN"
        assert len(data["general_tips"]) == 2

    async def test_200_us_locale(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        with patch(
            "src.api.routes.compensation.compensation_coach_agent",
            new=AsyncMock(return_value=_mock_agent_response()),
        ):
            response = await client.post(
                "/compensation/salary-coach",
                json={
                    "current_salary": 150000,
                    "target_range_min": 180000,
                    "target_range_max": 220000,
                    "role_title": "Staff Engineer",
                    "company_name": "BigTech",
                    "locale": "US",
                    "city": "San Francisco",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["locale_used"] == "US"

    async def test_requires_auth(self, client: AsyncClient) -> None:
        response = await client.post(
            "/compensation/salary-coach",
            json={
                "current_ctc": 1500000,
                "target_range_min": 2000000,
                "target_range_max": 2500000,
                "role_title": "Dev",
                "company_name": "Corp",
            },
        )
        assert response.status_code in (401, 403)

    async def test_422_no_comp_provided(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.post(
            "/compensation/salary-coach",
            json={
                "target_range_min": 2000000,
                "target_range_max": 2500000,
                "role_title": "Dev",
                "company_name": "Corp",
            },
        )
        assert response.status_code == 422

    async def test_422_missing_required_fields(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        response = await client.post(
            "/compensation/salary-coach",
            json={"current_ctc": 1500000},
        )
        assert response.status_code == 422

    async def test_with_company_context(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        with patch(
            "src.api.routes.compensation.compensation_coach_agent",
            new=AsyncMock(return_value=_mock_agent_response()),
        ):
            response = await client.post(
                "/compensation/salary-coach",
                json={
                    "current_ctc": 1500000,
                    "target_range_min": 2000000,
                    "target_range_max": 2500000,
                    "role_title": "Dev",
                    "company_name": "Startup",
                    "company_context": "Series B, well funded",
                },
            )

        assert response.status_code == 200
