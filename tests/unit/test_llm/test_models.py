"""
Tests for LLM types, routing configuration, and cost constants.

These tests verify the structural integrity of the routing and cost tables
rather than runtime behavior. They catch configuration errors early:
- Missing task types in the routing table
- Models referenced in routing but absent from the cost table
- Enum serialization mismatches
"""

from src.llm.models import (
    COST_PER_MILLION_TOKENS,
    ROUTING_TABLE,
    CircuitState,
    ModelConfig,
    ProviderName,
    TaskType,
)


class TestTaskType:
    """Verify TaskType enum values and serialization."""

    def test_all_task_types_are_strings(self):
        """StrEnum values serialize to lowercase strings."""
        for task in TaskType:
            assert isinstance(task.value, str)
            assert task.value == task.value.lower()

    def test_expected_task_types_exist(self):
        """All planned task types are defined."""
        expected = {
            "cover_letter",
            "resume_tailoring",
            "job_matching",
            "company_research",
            "quick_chat",
            "data_extraction",
            "interview_prep",
            "outreach_message",
            "resume_parsing",
            "star_story",
            "mock_interview",
            "general",
        }
        actual = {t.value for t in TaskType}
        assert actual == expected

    def test_task_type_string_comparison(self):
        """StrEnum allows direct string comparison."""
        assert TaskType.COVER_LETTER == "cover_letter"


class TestProviderName:
    """Verify ProviderName enum values."""

    def test_all_providers_are_strings(self):
        for provider in ProviderName:
            assert isinstance(provider.value, str)

    def test_expected_providers_exist(self):
        expected = {"anthropic", "openai", "groq"}
        actual = {p.value for p in ProviderName}
        assert actual == expected


class TestCircuitState:
    """Verify CircuitState enum values."""

    def test_expected_states_exist(self):
        expected = {"closed", "open", "half_open"}
        actual = {s.value for s in CircuitState}
        assert actual == expected


class TestModelConfig:
    """Verify ModelConfig dataclass behavior."""

    def test_creation_with_all_fields(self):
        config = ModelConfig(
            provider=ProviderName.ANTHROPIC,
            model_name="test-model",
            max_tokens=1024,
            temperature=0.5,
        )
        assert config.provider == ProviderName.ANTHROPIC
        assert config.model_name == "test-model"
        assert config.max_tokens == 1024
        assert config.temperature == 0.5

    def test_frozen_dataclass_is_immutable(self):
        """ModelConfig is frozen — prevents accidental mutation."""
        config = ModelConfig(
            provider=ProviderName.OPENAI,
            model_name="test",
            max_tokens=512,
            temperature=0.0,
        )
        try:
            config.max_tokens = 2048
            raise AssertionError("Should have raised FrozenInstanceError")
        except AttributeError:
            pass  # Expected — frozen dataclass prevents mutation.


class TestRoutingTable:
    """Verify routing table completeness and consistency."""

    def test_every_task_type_has_routing_entry(self):
        """All TaskType values appear in the routing table."""
        for task_type in TaskType:
            assert task_type in ROUTING_TABLE, (
                f"TaskType.{task_type.name} has no entry in ROUTING_TABLE"
            )

    def test_every_routing_entry_has_at_least_one_config(self):
        """Each task type maps to at least one model configuration."""
        for task_type, configs in ROUTING_TABLE.items():
            assert len(configs) >= 1, (
                f"ROUTING_TABLE[{task_type.name}] is empty"
            )

    def test_all_configs_are_model_config_instances(self):
        """Routing table entries contain ModelConfig, not raw dicts."""
        for task_type, configs in ROUTING_TABLE.items():
            for config in configs:
                assert isinstance(config, ModelConfig), (
                    f"ROUTING_TABLE[{task_type.name}] contains {type(config)}"
                )

    def test_all_configs_reference_valid_providers(self):
        """Every config in the routing table uses a known provider."""
        for task_type, configs in ROUTING_TABLE.items():
            for config in configs:
                assert config.provider in ProviderName, (
                    f"Unknown provider {config.provider} in "
                    f"ROUTING_TABLE[{task_type.name}]"
                )


class TestCostTable:
    """Verify cost table completeness and correctness."""

    def test_all_routed_models_have_cost_entries(self):
        """Every model referenced in the routing table has a cost entry."""
        routed_models = set()
        for configs in ROUTING_TABLE.values():
            for config in configs:
                routed_models.add(config.model_name)

        for model in routed_models:
            assert model in COST_PER_MILLION_TOKENS, (
                f"Model '{model}' in routing table but not in "
                f"COST_PER_MILLION_TOKENS"
            )

    def test_cost_entries_are_non_negative_tuples(self):
        """Cost entries are (input, output) tuples with non-negative values."""
        for model, (input_cost, output_cost) in COST_PER_MILLION_TOKENS.items():
            assert input_cost >= 0, f"Negative input cost for {model}"
            assert output_cost >= 0, f"Negative output cost for {model}"

    def test_groq_models_are_free(self):
        """Groq free tier models have zero cost."""
        groq_models = {
            config.model_name
            for configs in ROUTING_TABLE.values()
            for config in configs
            if config.provider == ProviderName.GROQ
        }
        for model in groq_models:
            input_cost, output_cost = COST_PER_MILLION_TOKENS[model]
            assert input_cost == 0.0, f"Groq model {model} has non-zero input cost"
            assert output_cost == 0.0, f"Groq model {model} has non-zero output cost"
