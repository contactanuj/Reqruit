"""Tests for the onboarding workflow graph."""

from unittest.mock import AsyncMock, patch

from src.workflows.graphs.onboarding import (
    build_onboarding_graph,
    coaching_session,
    generate_plan,
    get_onboarding_graph,
)


class TestGraphCompilation:
    def test_graph_compiles(self):
        graph = build_onboarding_graph()
        assert graph is not None

    def test_get_graph_singleton(self):
        graph = get_onboarding_graph()
        assert graph is not None

    def test_graph_has_expected_nodes(self):
        graph = build_onboarding_graph()
        node_names = set(graph.get_graph().nodes.keys())
        assert "generate_plan" in node_names
        assert "human_review" in node_names
        assert "coaching_session" in node_names
        assert "coaching_followup" in node_names


class TestGeneratePlanNode:
    async def test_calls_agent_and_returns_plan(self):
        mock_result = {
            "milestones": [
                {"title": "Meet team", "target_day": 1, "description": "Intro"},
            ]
        }

        mock_agent = AsyncMock(return_value=mock_result)
        with patch("src.workflows.graphs.onboarding.onboarding_plan_agent", mock_agent):
            state = {
                "messages": [],
                "company_name": "Acme Corp",
                "role_title": "Engineer",
                "skill_gaps": [],
                "plan": {},
                "jd_text": "",
                "coaching_query": "",
                "coaching_response": "",
                "feedback": "",
                "locale": "",
                "status": "generating",
            }
            config = {"configurable": {"thread_id": "test-123"}}

            result = await generate_plan(state, config)

            assert result["status"] == "plan_generated"
            assert "plan" in result

    async def test_appends_joining_prep_for_locale(self):
        mock_result = {"milestones": []}

        mock_agent = AsyncMock(return_value=mock_result)
        with patch("src.workflows.graphs.onboarding.onboarding_plan_agent", mock_agent):
            state = {
                "messages": [],
                "company_name": "Test Co",
                "role_title": "Dev",
                "skill_gaps": [],
                "plan": {},
                "jd_text": "",
                "coaching_query": "",
                "coaching_response": "",
                "feedback": "",
                "locale": "IN",
                "status": "generating",
            }
            config = {"configurable": {"thread_id": "test-locale"}}

            result = await generate_plan(state, config)

            plan = result["plan"]
            assert "joining_prep" in plan
            assert len(plan["joining_prep"]) > 0
            categories = [item["category"] for item in plan["joining_prep"]]
            assert "PF Transfer" in categories


class TestRevisionLoop:
    async def test_feedback_included_in_state(self):
        """When feedback is provided, it should be available in state for re-generation."""
        state = {
            "messages": [],
            "company_name": "Acme Corp",
            "role_title": "Engineer",
            "skill_gaps": [],
            "plan": {"milestones": []},
            "jd_text": "",
            "coaching_query": "",
            "coaching_response": "",
            "feedback": "Add more networking milestones",
            "locale": "",
            "status": "revising",
        }

        mock_agent = AsyncMock(return_value={"milestones": []})
        with patch("src.workflows.graphs.onboarding.onboarding_plan_agent", mock_agent):
            config = {"configurable": {"thread_id": "test-456"}}
            result = await generate_plan(state, config)
            assert result["status"] == "plan_generated"


class TestCoachingSessionNode:
    async def test_calls_coach_agent(self):
        mock_result = {
            "coaching_response": '{"whats_happening":"context","how_to_respond":"action","conversation_scripts":[],"when_to_escalate":"flags"}',
        }

        mock_agent = AsyncMock(return_value=mock_result)
        with patch("src.workflows.graphs.onboarding.onboarding_coach_agent", mock_agent):
            state = {
                "messages": [],
                "company_name": "Acme Corp",
                "role_title": "Engineer",
                "skill_gaps": [],
                "plan": {},
                "jd_text": "",
                "coaching_query": "My manager gives vague feedback",
                "coaching_response": "",
                "feedback": "",
                "locale": "",
                "status": "coaching",
            }
            config = {"configurable": {"thread_id": "test-coach"}}

            result = await coaching_session(state, config)

            assert result["status"] == "coaching_complete"
            assert "coaching_response" in result
            mock_agent.assert_called_once()

    async def test_returns_coaching_response(self):
        expected_response = '{"whats_happening":"This is normal","how_to_respond":"Talk to them","conversation_scripts":["Try saying..."],"when_to_escalate":"If it continues"}'
        mock_agent = AsyncMock(return_value={"coaching_response": expected_response})

        with patch("src.workflows.graphs.onboarding.onboarding_coach_agent", mock_agent):
            state = {
                "messages": [],
                "company_name": "",
                "role_title": "",
                "skill_gaps": [],
                "plan": {},
                "jd_text": "",
                "coaching_query": "Feeling lost",
                "coaching_response": "",
                "feedback": "",
                "locale": "",
                "status": "",
            }
            config = {"configurable": {"thread_id": "test-resp"}}

            result = await coaching_session(state, config)
            assert result["coaching_response"] == expected_response
