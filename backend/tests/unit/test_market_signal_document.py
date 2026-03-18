"""Tests for the MarketSignal document model."""

from beanie import PydanticObjectId

from src.db.documents.market_signal import MarketSignal


class TestMarketSignal:
    """Tests for the MarketSignal document model."""

    def test_create_with_required_fields(self) -> None:
        signal = MarketSignal(
            signal_type="hiring_trend",
            user_id=PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa"),
        )
        assert signal.signal_type == "hiring_trend"
        assert str(signal.user_id) == "aaaaaaaaaaaaaaaaaaaaaaaa"

    def test_default_values(self) -> None:
        signal = MarketSignal(signal_type="layoff_alert")
        assert signal.severity == "info"
        assert signal.title == ""
        assert signal.description == ""
        assert signal.industry == ""
        assert signal.region == ""
        assert signal.source == ""
        assert signal.confidence == 0.0
        assert signal.tags == []
        assert signal.expires_at is None
        assert signal.metadata == {}

    def test_optional_user_id_defaults_to_none(self) -> None:
        signal = MarketSignal(signal_type="disruption")
        assert signal.user_id is None

    def test_user_id_can_be_set(self) -> None:
        signal = MarketSignal(
            signal_type="skill_demand",
            user_id=PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb"),
        )
        assert str(signal.user_id) == "bbbbbbbbbbbbbbbbbbbbbbbb"

    def test_settings_name(self) -> None:
        assert MarketSignal.Settings.name == "market_signals"
