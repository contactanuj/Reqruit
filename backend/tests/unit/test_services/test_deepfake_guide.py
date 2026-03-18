"""Tests for DeepfakeInterviewGuide — static checklist."""

from src.services.trust.deepfake_guide import DeepfakeInterviewGuide


class TestDeepfakeInterviewGuide:
    def test_returns_checklist_with_4_categories(self):
        guide = DeepfakeInterviewGuide.get_guide()
        assert len(guide.categories) == 4

    def test_audio_visual_sync_has_4_items(self):
        guide = DeepfakeInterviewGuide.get_guide()
        av_category = next(c for c in guide.categories if "Audio" in c.category_name)
        assert len(av_category.items) >= 4

    def test_identity_verification_has_5_items(self):
        guide = DeepfakeInterviewGuide.get_guide()
        id_category = next(c for c in guide.categories if "Identity" in c.category_name)
        assert len(id_category.items) >= 5

    def test_all_items_have_required_fields(self):
        guide = DeepfakeInterviewGuide.get_guide()
        for category in guide.categories:
            for item in category.items:
                assert item.check
                assert item.description
                assert item.severity in ("critical", "important", "informational")

    def test_red_flag_category_exists(self):
        guide = DeepfakeInterviewGuide.get_guide()
        names = [c.category_name for c in guide.categories]
        assert any("Red Flag" in n for n in names)

    def test_background_category_exists(self):
        guide = DeepfakeInterviewGuide.get_guide()
        names = [c.category_name for c in guide.categories]
        assert any("Background" in n for n in names)

    def test_has_last_updated(self):
        guide = DeepfakeInterviewGuide.get_guide()
        assert guide.last_updated
