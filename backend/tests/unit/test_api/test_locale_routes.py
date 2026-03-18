"""
Unit tests for locale routes.

Covers:
    GET   /locale/profile                  — get locale profile
    PATCH /locale/profile                  — update locale profile
    POST  /locale/compensation/ctc-decode  — CTC breakdown
    POST  /locale/compensation/compare     — salary comparison
    POST  /locale/notice-period/calculate  — notice period calculation
"""

from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import get_current_user, get_locale_service, get_market_config_repository
from src.services.locale_service import CompensationComponent, IndianCompensation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(with_locale=False):
    user = MagicMock()
    user.id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
    user.email = "test@example.com"
    user.is_active = True

    if with_locale:
        profile = MagicMock()
        profile.model_dump.return_value = {
            "primary_market": "IN",
            "target_markets": ["US"],
            "nationality": "IN",
        }
        profile.primary_market = "IN"
        profile.notice_period = MagicMock()
        profile.notice_period.contractual_days = 0
        profile.consent_granted_at = None
        user.locale_profile = profile
    else:
        user.locale_profile = None

    return user


def _make_locale_service():
    svc = MagicMock()
    svc.decode_ctc.return_value = IndianCompensation(
        ctc_annual=1_000_000,
        basic=400_000,
        hra=200_000,
        special_allowance=132_760,
        employer_pf=48_000,
        employee_pf=48_000,
        gratuity=19_240,
        in_hand_monthly=60_000,
        tax_annual_estimated=40_000,
        components=[
            CompensationComponent(name="Basic", value=400_000, pct_of_ctc=40.0),
        ],
    )
    svc.compare_salary = AsyncMock(return_value={
        "source": {"amount": 1_000_000, "currency": "INR", "region": "IN"},
        "target": {"nominal_conversion": 12_000, "currency": "USD"},
        "ppp_adjusted": {"equivalent": 45_454.55},
        "confidence_level": "HIGH",
    })
    svc.calculate_notice.return_value = {
        "remaining_days": 50,
        "earliest_joining_date": "2026-05-01T00:00:00",
    }
    return svc


# ---------------------------------------------------------------------------
# GET /locale/profile
# ---------------------------------------------------------------------------


class TestGetLocaleProfile:
    async def test_returns_profile(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        user = _make_user(with_locale=True)
        app.dependency_overrides[get_current_user] = lambda: user
        try:
            response = await client.get("/locale/profile")
            assert response.status_code == 200
            data = response.json()
            assert data["primary_market"] == "IN"
        finally:
            app.dependency_overrides.clear()

    async def test_returns_404_when_no_profile(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        user = _make_user(with_locale=False)
        app.dependency_overrides[get_current_user] = lambda: user
        try:
            response = await client.get("/locale/profile")
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    async def test_requires_auth(self, client: AsyncClient) -> None:
        response = await client.get("/locale/profile")
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# PATCH /locale/profile
# ---------------------------------------------------------------------------


class TestUpdateLocaleProfile:
    async def test_update_profile(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        user = _make_user(with_locale=True)
        user.set = AsyncMock()

        mock_repo = MagicMock()
        mock_repo.get_by_region = AsyncMock(return_value=MagicMock())

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_market_config_repository] = lambda: mock_repo
        try:
            response = await client.patch(
                "/locale/profile",
                json={"primary_market": "US"},
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    async def test_update_invalid_market_returns_400(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        user = _make_user(with_locale=True)

        mock_repo = MagicMock()
        mock_repo.get_by_region = AsyncMock(return_value=None)

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_market_config_repository] = lambda: mock_repo
        try:
            response = await client.patch(
                "/locale/profile",
                json={"primary_market": "ZZ"},
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /locale/compensation/ctc-decode
# ---------------------------------------------------------------------------


class TestDecodeCTC:
    async def test_decode_ctc_success(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        user = _make_user()
        svc = _make_locale_service()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_locale_service] = lambda: svc
        try:
            response = await client.post(
                "/locale/compensation/ctc-decode",
                json={"ctc_annual": 1_000_000},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["ctc_annual"] == 1_000_000
            assert data["basic"] == 400_000
        finally:
            app.dependency_overrides.clear()

    async def test_decode_ctc_negative_amount(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        user = _make_user()
        svc = _make_locale_service()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_locale_service] = lambda: svc
        try:
            response = await client.post(
                "/locale/compensation/ctc-decode",
                json={"ctc_annual": -100},
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    async def test_decode_ctc_invalid_city_type(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        user = _make_user()
        svc = _make_locale_service()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_locale_service] = lambda: svc
        try:
            response = await client.post(
                "/locale/compensation/ctc-decode",
                json={"ctc_annual": 1_000_000, "city_type": "RURAL"},
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    async def test_decode_ctc_invalid_tax_regime(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        user = _make_user()
        svc = _make_locale_service()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_locale_service] = lambda: svc
        try:
            response = await client.post(
                "/locale/compensation/ctc-decode",
                json={"ctc_annual": 1_000_000, "tax_regime": "FLAT"},
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /locale/compensation/compare
# ---------------------------------------------------------------------------


class TestCompareSalary:
    async def test_compare_success(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        user = _make_user()
        svc = _make_locale_service()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_locale_service] = lambda: svc
        try:
            response = await client.post(
                "/locale/compensation/compare",
                json={"source_amount": 1_000_000},
            )
            assert response.status_code == 200
            data = response.json()
            assert "source" in data
        finally:
            app.dependency_overrides.clear()

    async def test_compare_negative_amount(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        user = _make_user()
        svc = _make_locale_service()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_locale_service] = lambda: svc
        try:
            response = await client.post(
                "/locale/compensation/compare",
                json={"source_amount": -500},
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /locale/notice-period/calculate
# ---------------------------------------------------------------------------


class TestCalculateNoticePeriod:
    async def test_joining_date(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        user = _make_user()
        svc = _make_locale_service()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_locale_service] = lambda: svc
        try:
            response = await client.post(
                "/locale/notice-period/calculate",
                json={"action": "JOINING_DATE", "contractual_days": 60, "served_days": 10},
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    async def test_invalid_action(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        user = _make_user()
        svc = _make_locale_service()

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_locale_service] = lambda: svc
        try:
            response = await client.post(
                "/locale/notice-period/calculate",
                json={"action": "INVALID"},
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()
