"""
Tests for negotiation API routes.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import (
    get_current_user,
    get_negotiation_session_repository,
    get_offer_repository,
    get_salary_benchmark_repository,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user():
    user = MagicMock()
    user.id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
    user.email = "test@example.com"
    user.is_active = True
    return user


def _make_component(name="Base Salary", value=2000000):
    comp = MagicMock()
    comp.name = name
    comp.value = value
    comp.currency = "INR"
    comp.frequency = "annual"
    return comp


def _make_offer(user_id):
    offer = MagicMock()
    offer.id = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")
    offer.user_id = user_id
    offer.company_name = "Acme Corp"
    offer.role_title = "SDE-2"
    offer.total_comp_annual = 2500000.0
    offer.locale_market = "IN"
    offer.components = [_make_component()]
    return offer


def _make_session_repo():
    repo = MagicMock()
    repo.create = AsyncMock()
    repo.get_user_sessions = AsyncMock(return_value=[])
    repo.get_by_user_and_id = AsyncMock(return_value=None)
    repo.delete_by_user_and_id = AsyncMock(return_value=False)
    return repo


def _override(app, user, offer_repo, benchmark_repo=None, session_repo=None):
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_offer_repository] = lambda: offer_repo
    if benchmark_repo is not None:
        app.dependency_overrides[get_salary_benchmark_repository] = lambda: benchmark_repo
    if session_repo is None:
        session_repo = _make_session_repo()
    app.dependency_overrides[get_negotiation_session_repository] = lambda: session_repo


# ---------------------------------------------------------------------------
# POST /negotiation/simulate
# ---------------------------------------------------------------------------


class TestSimulateNegotiation:

    async def test_simulate_202(self, client: AsyncClient) -> None:
        user = _make_user()
        offer = _make_offer(user.id)
        offer_repo = MagicMock()
        offer_repo.get_by_user_and_id = AsyncMock(return_value=offer)
        offer_repo.compare_offers = AsyncMock(return_value=[])
        benchmark_repo = MagicMock()
        _override(client.app, user, offer_repo, benchmark_repo)

        # Mock market positioning
        mock_market = MagicMock()
        mock_market.data_available = False

        # Mock the graph
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value={
            "simulation_transcript": [
                {
                    "role": "recruiter",
                    "content": "Thank you for considering our offer.",
                    "coaching_feedback": "Opening from recruiter.",
                    "turn_number": 1,
                }
            ],
            "status": "simulating",
        })

        with (
            patch(
                "src.api.routes.negotiation.compute_market_position",
                new_callable=AsyncMock,
                return_value=mock_market,
            ),
            patch(
                "src.api.routes.negotiation.get_negotiation_graph",
                return_value=mock_graph,
            ),
        ):
            response = await client.post(
                "/negotiation/simulate",
                json={
                    "offer_id": str(offer.id),
                    "negotiation_goals": {"target_salary": 3000000},
                },
            )

        assert response.status_code == 202
        data = response.json()
        assert "thread_id" in data
        assert data["recruiter_response"] == "Thank you for considering our offer."
        assert data["turn_number"] == 1

    async def test_simulate_offer_not_found(self, client: AsyncClient) -> None:
        user = _make_user()
        offer_repo = MagicMock()
        offer_repo.get_by_user_and_id = AsyncMock(return_value=None)
        benchmark_repo = MagicMock()
        _override(client.app, user, offer_repo, benchmark_repo)

        response = await client.post(
            "/negotiation/simulate",
            json={"offer_id": "cccccccccccccccccccccccc"},
        )

        assert response.status_code == 404

    async def test_simulate_requires_auth(self, client: AsyncClient) -> None:
        response = await client.post(
            "/negotiation/simulate",
            json={"offer_id": "cccccccccccccccccccccccc"},
        )
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /negotiation/{thread_id}/respond
# ---------------------------------------------------------------------------


class TestRespondToNegotiation:

    async def test_respond_200(self, client: AsyncClient) -> None:
        user = _make_user()
        offer_repo = MagicMock()
        benchmark_repo = MagicMock()
        _override(client.app, user, offer_repo, benchmark_repo)

        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value={
            "simulation_transcript": [
                {"role": "recruiter", "content": "Opening.", "coaching_feedback": "", "tactic_detected": "", "turn_number": 1},
                {"role": "user", "content": "I want more.", "turn_number": 2},
                {"role": "recruiter", "content": "Let me check.", "coaching_feedback": "Good anchoring.", "tactic_detected": "anchoring", "turn_number": 2},
            ],
            "status": "simulating",
        })

        with patch(
            "src.api.routes.negotiation.get_negotiation_graph",
            return_value=mock_graph,
        ):
            response = await client.post(
                "/negotiation/test-thread-123/respond",
                json={"user_response": "I want more."},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["recruiter_response"] == "Let me check."
        assert data["tactic_detected"] == "anchoring"
        assert data["simulation_complete"] is False

    async def test_respond_simulation_complete(self, client: AsyncClient) -> None:
        user = _make_user()
        offer_repo = MagicMock()
        benchmark_repo = MagicMock()
        _override(client.app, user, offer_repo, benchmark_repo)

        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value={
            "simulation_transcript": [
                {"role": "recruiter", "content": "Deal!", "coaching_feedback": "Well done.", "tactic_detected": "closing", "turn_number": 5},
            ],
            "status": "complete",
        })

        with patch(
            "src.api.routes.negotiation.get_negotiation_graph",
            return_value=mock_graph,
        ):
            response = await client.post(
                "/negotiation/test-thread/respond",
                json={"user_response": "I accept."},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["simulation_complete"] is True

    async def test_respond_requires_auth(self, client: AsyncClient) -> None:
        response = await client.post(
            "/negotiation/test-thread/respond",
            json={"user_response": "Hello"},
        )
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /negotiation/scripts
# ---------------------------------------------------------------------------


class TestGenerateScripts:

    async def test_scripts_200(self, client: AsyncClient) -> None:
        user = _make_user()
        offer = _make_offer(user.id)
        offer_repo = MagicMock()
        offer_repo.get_by_user_and_id = AsyncMock(return_value=offer)
        benchmark_repo = MagicMock()
        _override(client.app, user, offer_repo, benchmark_repo)

        mock_market = MagicMock()
        mock_market.data_available = False

        agent_result = {
            "opening_statement": "I'd like to discuss the offer.",
            "branches": [
                {
                    "scenario_name": "acceptance",
                    "recruiter_response": "We can do that.",
                    "recommended_user_response": "Great.",
                    "reasoning": "Lock in.",
                    "risk_assessment": "safe",
                },
                {
                    "scenario_name": "pushback",
                    "recruiter_response": "That's high.",
                    "recommended_user_response": "Market data shows...",
                    "reasoning": "Data anchoring.",
                    "risk_assessment": "moderate",
                },
                {
                    "scenario_name": "rejection",
                    "recruiter_response": "No.",
                    "recommended_user_response": "What about non-salary?",
                    "reasoning": "Pivot.",
                    "risk_assessment": "safe",
                },
            ],
            "non_salary_tactics": [
                {"priority": "remote_work", "script": "Could we discuss remote?", "fallback": "Hybrid?"}
            ],
            "general_tips": ["Stay calm"],
        }

        with (
            patch(
                "src.api.routes.negotiation.compute_market_position",
                new_callable=AsyncMock,
                return_value=mock_market,
            ),
            patch(
                "src.agents.script_generator.ScriptGeneratorAgent",
            ) as MockAgent,
        ):
            mock_instance = AsyncMock(return_value=agent_result)
            MockAgent.return_value = mock_instance

            response = await client.post(
                "/negotiation/scripts",
                json={
                    "offer_id": str(offer.id),
                    "target_total_comp": 3000000,
                    "priorities": ["salary", "remote_work"],
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["opening_statement"] == "I'd like to discuss the offer."
        assert len(data["branches"]) == 3
        assert data["branches"][0]["scenario_name"] == "acceptance"
        assert data["branches"][1]["risk_assessment"] == "moderate"
        assert len(data["non_salary_tactics"]) == 1
        assert data["non_salary_tactics"][0]["priority"] == "remote_work"

    async def test_scripts_offer_not_found(self, client: AsyncClient) -> None:
        user = _make_user()
        offer_repo = MagicMock()
        offer_repo.get_by_user_and_id = AsyncMock(return_value=None)
        benchmark_repo = MagicMock()
        _override(client.app, user, offer_repo, benchmark_repo)

        response = await client.post(
            "/negotiation/scripts",
            json={
                "offer_id": "cccccccccccccccccccccccc",
                "target_total_comp": 3000000,
                "priorities": [],
            },
        )

        assert response.status_code == 404

    async def test_scripts_requires_auth(self, client: AsyncClient) -> None:
        response = await client.post(
            "/negotiation/scripts",
            json={
                "offer_id": "cccccccccccccccccccccccc",
                "target_total_comp": 3000000,
            },
        )
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /negotiation/decide
# ---------------------------------------------------------------------------


class TestDecideOffers:

    async def test_decide_200(self, client: AsyncClient) -> None:
        user = _make_user()
        o1 = _make_offer(user.id)
        o2 = MagicMock()
        o2.id = PydanticObjectId("cccccccccccccccccccccccc")
        o2.user_id = user.id
        o2.company_name = "Beta Inc"
        o2.role_title = "SDE-3"
        o2.total_comp_annual = 3500000.0
        o2.locale_market = "IN"
        o2.components = [_make_component(value=3500000)]

        offer_repo = MagicMock()
        offer_repo.compare_offers = AsyncMock(return_value=[o1, o2])
        benchmark_repo = MagicMock()
        _override(client.app, user, offer_repo, benchmark_repo)

        response = await client.post(
            "/negotiation/decide",
            json={
                "offer_ids": [str(o1.id), str(o2.id)],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["offers"]) == 2
        assert data["recommended_choice"]
        assert data["recommended_company"]
        assert data["weights_are_defaults"] is True
        assert len(data["criteria_weights"]) == 5

    async def test_decide_fewer_than_2_offers_422(self, client: AsyncClient) -> None:
        user = _make_user()
        offer_repo = MagicMock()
        benchmark_repo = MagicMock()
        _override(client.app, user, offer_repo, benchmark_repo)

        response = await client.post(
            "/negotiation/decide",
            json={
                "offer_ids": ["aaaaaaaaaaaaaaaaaaaaaaaa"],
            },
        )

        assert response.status_code == 422

    async def test_decide_invalid_weights_422(self, client: AsyncClient) -> None:
        user = _make_user()
        offer_repo = MagicMock()
        benchmark_repo = MagicMock()
        _override(client.app, user, offer_repo, benchmark_repo)

        response = await client.post(
            "/negotiation/decide",
            json={
                "offer_ids": [
                    "aaaaaaaaaaaaaaaaaaaaaaaa",
                    "bbbbbbbbbbbbbbbbbbbbbbbb",
                ],
                "criteria_weights": {"compensation": 0.9, "growth": 0.9},
            },
        )

        assert response.status_code == 422

    async def test_decide_offer_not_found(self, client: AsyncClient) -> None:
        user = _make_user()
        offer_repo = MagicMock()
        offer_repo.compare_offers = AsyncMock(return_value=[_make_offer(user.id)])
        benchmark_repo = MagicMock()
        _override(client.app, user, offer_repo, benchmark_repo)

        response = await client.post(
            "/negotiation/decide",
            json={
                "offer_ids": [
                    "aaaaaaaaaaaaaaaaaaaaaaaa",
                    "bbbbbbbbbbbbbbbbbbbbbbbb",
                ],
            },
        )

        assert response.status_code == 404

    async def test_decide_requires_auth(self, client: AsyncClient) -> None:
        response = await client.post(
            "/negotiation/decide",
            json={
                "offer_ids": [
                    "aaaaaaaaaaaaaaaaaaaaaaaa",
                    "bbbbbbbbbbbbbbbbbbbbbbbb",
                ],
            },
        )
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /negotiation/sessions
# ---------------------------------------------------------------------------


def _make_session_obj(session_type="simulation", status="active"):
    from datetime import datetime, timezone

    session = MagicMock()
    session.id = PydanticObjectId("dddddddddddddddddddddddd")
    session.offer_id = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")
    session.session_type = session_type
    session.status = status
    session.thread_id = "thread-abc"
    session.transcript = [{"role": "recruiter", "content": "Hello"}]
    session.scripts = []
    session.decision_matrix = {}
    session.created_at = datetime(2025, 6, 1, tzinfo=timezone.utc)
    return session


class TestListSessions:

    async def test_list_sessions_200(self, client: AsyncClient) -> None:
        user = _make_user()
        session_repo = _make_session_repo()
        session_repo.get_user_sessions = AsyncMock(
            return_value=[_make_session_obj()]
        )
        offer_repo = MagicMock()
        _override(client.app, user, offer_repo, session_repo=session_repo)

        response = await client.get("/negotiation/sessions")

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert len(data["items"]) == 1
        assert data["items"][0]["session_type"] == "simulation"

    async def test_list_sessions_pagination(self, client: AsyncClient) -> None:
        user = _make_user()
        session_repo = _make_session_repo()
        session_repo.get_user_sessions = AsyncMock(return_value=[])
        offer_repo = MagicMock()
        _override(client.app, user, offer_repo, session_repo=session_repo)

        response = await client.get("/negotiation/sessions?page=2&page_size=5")

        assert response.status_code == 200
        session_repo.get_user_sessions.assert_called_once()
        call_kwargs = session_repo.get_user_sessions.call_args
        assert call_kwargs[1]["skip"] == 5
        assert call_kwargs[1]["limit"] == 5

    async def test_list_sessions_requires_auth(self, client: AsyncClient) -> None:
        response = await client.get("/negotiation/sessions")
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /negotiation/sessions/{session_id}
# ---------------------------------------------------------------------------


class TestGetSession:

    async def test_get_session_200(self, client: AsyncClient) -> None:
        user = _make_user()
        session_obj = _make_session_obj()
        session_repo = _make_session_repo()
        session_repo.get_by_user_and_id = AsyncMock(return_value=session_obj)
        offer_repo = MagicMock()
        _override(client.app, user, offer_repo, session_repo=session_repo)

        response = await client.get(
            f"/negotiation/sessions/{session_obj.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_type"] == "simulation"
        assert data["thread_id"] == "thread-abc"
        assert len(data["transcript"]) == 1

    async def test_get_session_not_found(self, client: AsyncClient) -> None:
        user = _make_user()
        session_repo = _make_session_repo()
        session_repo.get_by_user_and_id = AsyncMock(return_value=None)
        offer_repo = MagicMock()
        _override(client.app, user, offer_repo, session_repo=session_repo)

        response = await client.get(
            "/negotiation/sessions/cccccccccccccccccccccccc"
        )

        assert response.status_code == 404

    async def test_get_session_requires_auth(self, client: AsyncClient) -> None:
        response = await client.get(
            "/negotiation/sessions/cccccccccccccccccccccccc"
        )
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# DELETE /negotiation/sessions/{session_id}
# ---------------------------------------------------------------------------


class TestDeleteSession:

    async def test_delete_session_204(self, client: AsyncClient) -> None:
        user = _make_user()
        session_repo = _make_session_repo()
        session_repo.delete_by_user_and_id = AsyncMock(return_value=True)
        offer_repo = MagicMock()
        _override(client.app, user, offer_repo, session_repo=session_repo)

        response = await client.delete(
            "/negotiation/sessions/cccccccccccccccccccccccc"
        )

        assert response.status_code == 204

    async def test_delete_session_not_found(self, client: AsyncClient) -> None:
        user = _make_user()
        session_repo = _make_session_repo()
        session_repo.delete_by_user_and_id = AsyncMock(return_value=False)
        offer_repo = MagicMock()
        _override(client.app, user, offer_repo, session_repo=session_repo)

        response = await client.delete(
            "/negotiation/sessions/cccccccccccccccccccccccc"
        )

        assert response.status_code == 404

    async def test_delete_session_requires_auth(self, client: AsyncClient) -> None:
        response = await client.delete(
            "/negotiation/sessions/cccccccccccccccccccccccc"
        )
        assert response.status_code in (401, 403)
