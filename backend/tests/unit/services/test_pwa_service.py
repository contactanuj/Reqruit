"""Tests for PWA service — manifest and mobile feature detection."""

from src.services.pwa_service import get_mobile_features, get_pwa_manifest


class TestGetPwaManifest:
    def test_has_required_fields(self):
        manifest = get_pwa_manifest()
        assert manifest["name"]
        assert manifest["short_name"] == "Reqruit"
        assert manifest["start_url"] == "/"
        assert manifest["display"] == "standalone"

    def test_has_icons(self):
        manifest = get_pwa_manifest()
        assert len(manifest["icons"]) >= 2
        sizes = [icon["sizes"] for icon in manifest["icons"]]
        assert "192x192" in sizes
        assert "512x512" in sizes

    def test_has_theme_colors(self):
        manifest = get_pwa_manifest()
        assert manifest["background_color"]
        assert manifest["theme_color"]


class TestGetMobileFeatures:
    def test_has_feature_flags(self):
        features = get_mobile_features()
        assert "features" in features
        assert features["features"]["job_discovery"] is True
        assert features["features"]["application_tracking"] is True

    def test_has_ui_hints(self):
        features = get_mobile_features()
        assert "ui_hints" in features
        assert features["ui_hints"]["compact_navigation"] is True
        assert features["ui_hints"]["bottom_tab_bar"] is True

    def test_push_notifications_enabled(self):
        features = get_mobile_features()
        assert features["features"]["push_notifications"] is True
