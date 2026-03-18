"""Tests for PWA routes — manifest and mobile features."""

from httpx import AsyncClient


class TestManifest:
    async def test_returns_manifest(self, client: AsyncClient):
        resp = await client.get("/manifest.json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["short_name"] == "Reqruit"
        assert data["display"] == "standalone"
        assert len(data["icons"]) >= 2

    async def test_manifest_has_start_url(self, client: AsyncClient):
        resp = await client.get("/manifest.json")
        data = resp.json()
        assert data["start_url"] == "/"


class TestMobileFeatures:
    async def test_returns_features(self, client: AsyncClient):
        resp = await client.get("/mobile/features")
        assert resp.status_code == 200
        data = resp.json()
        assert data["features"]["job_discovery"] is True
        assert "ui_hints" in data

    async def test_feature_flags_are_booleans(self, client: AsyncClient):
        resp = await client.get("/mobile/features")
        data = resp.json()
        for value in data["features"].values():
            assert isinstance(value, bool)
