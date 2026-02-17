"""
Tests for the health check endpoint.

This is the first test in the project — verifies that the FastAPI app factory,
configuration loading, and basic routing all work end-to-end.
"""

from httpx import AsyncClient


async def test_health_returns_200(client: AsyncClient) -> None:
    """Health endpoint should return 200 with app metadata."""
    response = await client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "environment" in data


async def test_health_response_structure(client: AsyncClient) -> None:
    """Health response should contain all expected fields."""
    response = await client.get("/health")
    data = response.json()

    expected_fields = {"status", "app", "version", "environment"}
    assert set(data.keys()) == expected_fields
