"""
Offer repository — owner-scoped CRUD for compensation offers.

All queries are scoped to a user_id for ownership enforcement.
"""

from beanie import PydanticObjectId

from src.db.documents.offer import NegotiationOutcome, Offer
from src.repositories.base import BaseRepository


class OfferRepository(BaseRepository[Offer]):
    """Offer data access methods extending the generic BaseRepository."""

    def __init__(self) -> None:
        super().__init__(Offer)

    async def get_by_user_and_id(
        self, user_id: PydanticObjectId, offer_id: PydanticObjectId
    ) -> Offer | None:
        """Fetch a specific offer, verifying ownership by user_id."""
        return await self.find_one({"_id": offer_id, "user_id": user_id})

    async def get_user_offers(
        self, user_id: PydanticObjectId, skip: int = 0, limit: int = 100
    ) -> list[Offer]:
        """List all offers for a user, sorted newest first."""
        return await self.find_many(
            {"user_id": user_id}, skip=skip, limit=limit, sort="-created_at"
        )

    async def compare_offers(
        self, user_id: PydanticObjectId, offer_ids: list[PydanticObjectId]
    ) -> list[Offer]:
        """Fetch multiple offers by ID for side-by-side comparison, scoped by user."""
        return await self.find_many(
            {"user_id": user_id, "_id": {"$in": offer_ids}}
        )

    async def record_outcome(
        self,
        offer_id: PydanticObjectId,
        user_id: PydanticObjectId,
        outcome: NegotiationOutcome,
        role_family: str = "",
        company_stage: str = "",
        region: str = "",
    ) -> Offer | None:
        """Record a negotiation outcome on an offer, computing deltas server-side."""
        offer = await self.get_by_user_and_id(user_id, offer_id)
        if offer is None:
            return None
        offer.negotiation_outcome = outcome
        offer.negotiation_initial_offer = outcome.initial_offer_total
        offer.negotiation_final_offer = outcome.final_offer_total
        offer.negotiation_delta = outcome.delta_absolute
        if role_family:
            offer.role_family = role_family
        if company_stage:
            offer.company_stage = company_stage
        if region:
            offer.region = region
        await offer.save()
        return offer

    async def get_negotiation_history(
        self, user_id: PydanticObjectId
    ) -> list[Offer]:
        """Return all offers with recorded negotiation outcomes, newest first."""
        return await self.find_many(
            {"user_id": user_id, "negotiation_outcome": {"$ne": None}},
            sort="-created_at",
        )

    async def get_strategy_success_rates(
        self, user_id: PydanticObjectId
    ) -> dict[str, dict]:
        """Aggregate outcomes by strategy_used for a user.

        Returns {strategy: {count, avg_delta_pct, success_rate}}.
        Success = delta_percentage > 0.
        """
        offers = await self.get_negotiation_history(user_id)
        strategies: dict[str, dict] = {}
        for offer in offers:
            outcome = offer.negotiation_outcome
            if outcome is None:
                continue
            strategy = outcome.strategy_used
            if strategy not in strategies:
                strategies[strategy] = {
                    "count": 0,
                    "total_delta_pct": 0.0,
                    "successes": 0,
                }
            strategies[strategy]["count"] += 1
            strategies[strategy]["total_delta_pct"] += outcome.delta_percentage
            if outcome.delta_percentage > 0:
                strategies[strategy]["successes"] += 1

        result = {}
        for strategy, data in strategies.items():
            count = data["count"]
            result[strategy] = {
                "count": count,
                "avg_delta_pct": round(data["total_delta_pct"] / count, 2) if count else 0.0,
                "success_rate": round(data["successes"] / count, 2) if count else 0.0,
            }
        return result

    async def get_anonymized_benchmarks(
        self,
        role_family: str,
        region: str,
        company_stage: str | None = None,
    ) -> dict:
        """Aggregate negotiation benchmarks across all users.

        Groups by (role_family, company_stage, region), counts distinct users.
        Only returns results when distinct user count >= 10 (NFR-P3-5).
        Never returns individual user data.
        """
        match_filter: dict = {
            "role_family": role_family,
            "region": region,
            "negotiation_outcome": {"$ne": None},
        }
        if company_stage:
            match_filter["company_stage"] = company_stage

        pipeline = [
            {"$match": match_filter},
            {"$group": {
                "_id": {
                    "role_family": "$role_family",
                    "company_stage": "$company_stage",
                    "region": "$region",
                },
                "distinct_users": {"$addToSet": "$user_id"},
                "avg_delta_pct": {"$avg": "$negotiation_outcome.delta_percentage"},
                "deltas": {"$push": "$negotiation_outcome.delta_percentage"},
                "strategies": {"$push": "$negotiation_outcome.strategy_used"},
            }},
            {"$addFields": {
                "cohort_size": {"$size": "$distinct_users"},
            }},
            # CRITICAL: Remove user_ids before returning
            {"$project": {"distinct_users": 0}},
        ]
        results = await Offer.aggregate(pipeline).to_list()
        return results[0] if results else {"cohort_size": 0}
