"""Tests for the Offer document model and OfferComponent embedded model."""

from beanie import PydanticObjectId

from src.db.documents.offer import Offer, OfferComponent


class TestOfferComponent:
    """Tests for OfferComponent embedded model."""

    def test_create_with_all_fields(self) -> None:
        comp = OfferComponent(
            name="Base Salary",
            value=1_500_000.0,
            currency="INR",
            frequency="annual",
            is_guaranteed=True,
            confidence="high",
            pct_of_total=60.0,
        )
        assert comp.name == "Base Salary"
        assert comp.value == 1_500_000.0
        assert comp.currency == "INR"
        assert comp.frequency == "annual"
        assert comp.is_guaranteed is True
        assert comp.confidence == "high"
        assert comp.pct_of_total == 60.0

    def test_defaults(self) -> None:
        comp = OfferComponent(name="Bonus", value=100_000.0)
        assert comp.currency == "INR"
        assert comp.frequency == "annual"
        assert comp.is_guaranteed is True
        assert comp.confidence == "high"
        assert comp.pct_of_total == 0.0

    def test_low_confidence(self) -> None:
        comp = OfferComponent(
            name="ESOPs",
            value=0.0,
            confidence="low",
            is_guaranteed=False,
        )
        assert comp.confidence == "low"
        assert comp.is_guaranteed is False


class TestOffer:
    """Tests for Offer document."""

    def test_collection_name(self) -> None:
        assert Offer.Settings.name == "offers"

    def test_create_with_required_fields(self) -> None:
        user_id = PydanticObjectId()
        offer = Offer(
            user_id=user_id,
            company_name="Acme Corp",
            role_title="SDE-2",
        )
        assert offer.user_id == user_id
        assert offer.company_name == "Acme Corp"
        assert offer.role_title == "SDE-2"
        assert offer.components == []
        assert offer.total_comp_annual == 0.0
        assert offer.application_id is None
        assert offer.market_percentile is None
        assert offer.negotiation_initial_offer is None
        assert offer.negotiation_final_offer is None
        assert offer.negotiation_delta is None
        assert offer.decision == ""
        assert offer.notes == ""
        assert offer.locale_market == ""
        assert offer.raw_text == ""
        assert offer.missing_fields == []
        assert offer.suggestions == []

    def test_create_with_all_fields(self) -> None:
        user_id = PydanticObjectId()
        app_id = PydanticObjectId()
        offer = Offer(
            user_id=user_id,
            application_id=app_id,
            company_name="TechCo",
            role_title="Staff Engineer",
            components=[
                OfferComponent(name="Base", value=3_000_000.0, pct_of_total=75.0),
                OfferComponent(
                    name="Bonus",
                    value=500_000.0,
                    frequency="annual",
                    is_guaranteed=False,
                    pct_of_total=12.5,
                ),
                OfferComponent(
                    name="ESOPs",
                    value=500_000.0,
                    frequency="annual",
                    is_guaranteed=False,
                    confidence="medium",
                    pct_of_total=12.5,
                ),
            ],
            total_comp_annual=4_000_000.0,
            market_percentile=75.0,
            decision="accepted",
            notes="Great offer",
            locale_market="IN",
            raw_text="Your CTC is 40 LPA...",
            missing_fields=["insurance_value"],
            suggestions=["Ask employer about insurance coverage"],
        )
        assert offer.application_id == app_id
        assert len(offer.components) == 3
        assert offer.total_comp_annual == 4_000_000.0
        assert offer.market_percentile == 75.0
        assert offer.locale_market == "IN"
        assert offer.missing_fields == ["insurance_value"]
        assert len(offer.suggestions) == 1

    def test_schema_version_default(self) -> None:
        offer = Offer(
            user_id=PydanticObjectId(),
            company_name="X",
            role_title="Y",
        )
        assert offer.schema_version == 1

    def test_timestamps_default_to_none(self) -> None:
        offer = Offer(
            user_id=PydanticObjectId(),
            company_name="X",
            role_title="Y",
        )
        assert offer.created_at is None
        assert offer.updated_at is None

    def test_indexes_defined(self) -> None:
        """Verify that custom indexes are defined on the model."""
        index_names = [idx.document.get("name", "") for idx in Offer.Settings.indexes]
        assert "user_created_idx" in index_names
