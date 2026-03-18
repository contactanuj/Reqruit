"""
Tests for memory recipe configuration.

Verifies that all configured agents have valid recipes, weights are in
valid ranges, and collection references match the known Weaviate and
MongoDB collections.
"""

import pytest

from src.db.weaviate_client import WEAVIATE_COLLECTIONS
from src.memory.recipes import MEMORY_RECIPES, MemoryRecipe

# ---------------------------------------------------------------------------
# Recipe structure
# ---------------------------------------------------------------------------


class TestMemoryRecipeStructure:
    def test_all_recipes_are_memory_recipe_instances(self):
        """Every entry in MEMORY_RECIPES is a MemoryRecipe."""
        for agent, recipe in MEMORY_RECIPES.items():
            assert isinstance(recipe, MemoryRecipe), (
                f"Recipe for '{agent}' is {type(recipe)}, expected MemoryRecipe"
            )

    def test_recipe_is_frozen(self):
        """MemoryRecipe instances are immutable (frozen dataclass)."""
        recipe = MEMORY_RECIPES["cover_letter_writer"]
        with pytest.raises(AttributeError):
            recipe.relevance_weight = 0.5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Weight validation
# ---------------------------------------------------------------------------


class TestWeightValidation:
    def test_relevance_weights_in_range(self):
        """All relevance_weight values are between 0.0 and 1.0."""
        for agent, recipe in MEMORY_RECIPES.items():
            assert 0.0 <= recipe.relevance_weight <= 1.0, (
                f"{agent}: relevance_weight={recipe.relevance_weight} out of range"
            )

    def test_recency_weights_in_range(self):
        """All recency_weight values are between 0.0 and 1.0."""
        for agent, recipe in MEMORY_RECIPES.items():
            assert 0.0 <= recipe.recency_weight <= 1.0, (
                f"{agent}: recency_weight={recipe.recency_weight} out of range"
            )

    def test_hybrid_alpha_in_range(self):
        """All hybrid_alpha values are between 0.0 and 1.0."""
        for agent, recipe in MEMORY_RECIPES.items():
            assert 0.0 <= recipe.hybrid_alpha <= 1.0, (
                f"{agent}: hybrid_alpha={recipe.hybrid_alpha} out of range"
            )

    def test_max_results_positive(self):
        """All max_results values are positive."""
        for agent, recipe in MEMORY_RECIPES.items():
            assert recipe.max_results > 0, (
                f"{agent}: max_results={recipe.max_results} must be positive"
            )


# ---------------------------------------------------------------------------
# Collection references
# ---------------------------------------------------------------------------


class TestCollectionReferences:
    def test_weaviate_collections_are_valid(self):
        """All referenced Weaviate collections exist in WEAVIATE_COLLECTIONS."""
        for agent, recipe in MEMORY_RECIPES.items():
            for coll in recipe.weaviate_collections:
                assert coll in WEAVIATE_COLLECTIONS, (
                    f"{agent}: references unknown Weaviate collection '{coll}'"
                )

    def test_weaviate_collections_are_tuples(self):
        """weaviate_collections uses tuples (not lists) for immutability."""
        for agent, recipe in MEMORY_RECIPES.items():
            assert isinstance(recipe.weaviate_collections, tuple), (
                f"{agent}: weaviate_collections should be a tuple"
            )

    def test_mongodb_collections_are_tuples(self):
        """mongodb_collections uses tuples (not lists) for immutability."""
        for agent, recipe in MEMORY_RECIPES.items():
            assert isinstance(recipe.mongodb_collections, tuple), (
                f"{agent}: mongodb_collections should be a tuple"
            )


# ---------------------------------------------------------------------------
# Known agents
# ---------------------------------------------------------------------------


class TestKnownAgents:
    def test_cover_letter_writer_has_recipe(self):
        """The cover_letter_writer agent has a memory recipe."""
        assert "cover_letter_writer" in MEMORY_RECIPES

    def test_requirements_analyst_has_recipe(self):
        """The requirements_analyst agent has a memory recipe."""
        assert "requirements_analyst" in MEMORY_RECIPES
