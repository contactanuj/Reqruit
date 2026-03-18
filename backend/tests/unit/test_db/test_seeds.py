"""Tests for the seed data loader."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from src.db.documents.market_config import MarketConfig
from src.db.seeds import seed_market_configs


class TestSeedMarketConfigs:
    """Tests for seed_market_configs()."""

    async def test_inserts_new_configs(self) -> None:
        seed_data = {"region_code": "IN", "region_name": "India"}
        mock_file = MagicMock(spec=Path)
        mock_file.name = "market_config_IN.json"
        mock_file.read_text.return_value = json.dumps(seed_data)

        with (
            patch("src.db.seeds._SEEDS_DIR") as mock_dir,
            patch.object(MarketConfig, "find_one", new_callable=AsyncMock, return_value=None),
            patch.object(MarketConfig, "insert", new_callable=AsyncMock),
        ):
            mock_dir.glob.return_value = [mock_file]
            inserted = await seed_market_configs()

        assert inserted == 1

    async def test_skips_existing_configs(self) -> None:
        seed_data = {"region_code": "IN", "region_name": "India"}
        mock_file = MagicMock(spec=Path)
        mock_file.name = "market_config_IN.json"
        mock_file.read_text.return_value = json.dumps(seed_data)

        existing = MagicMock(spec=MarketConfig)

        with (
            patch("src.db.seeds._SEEDS_DIR") as mock_dir,
            patch.object(MarketConfig, "find_one", new_callable=AsyncMock, return_value=existing),
        ):
            mock_dir.glob.return_value = [mock_file]
            inserted = await seed_market_configs()

        assert inserted == 0

    async def test_handles_missing_region_code(self) -> None:
        seed_data = {"region_name": "Unknown"}
        mock_file = MagicMock(spec=Path)
        mock_file.name = "market_config_XX.json"
        mock_file.read_text.return_value = json.dumps(seed_data)

        with patch("src.db.seeds._SEEDS_DIR") as mock_dir:
            mock_dir.glob.return_value = [mock_file]
            inserted = await seed_market_configs()

        assert inserted == 0

    async def test_no_seed_files(self) -> None:
        with patch("src.db.seeds._SEEDS_DIR") as mock_dir:
            mock_dir.glob.return_value = []
            inserted = await seed_market_configs()

        assert inserted == 0

    async def test_handles_json_error_gracefully(self) -> None:
        mock_file = MagicMock(spec=Path)
        mock_file.name = "market_config_BAD.json"
        mock_file.read_text.return_value = "not valid json"

        with patch("src.db.seeds._SEEDS_DIR") as mock_dir:
            mock_dir.glob.return_value = [mock_file]
            inserted = await seed_market_configs()

        assert inserted == 0


class TestSeedFiles:
    """Tests that actual seed JSON files are valid."""

    def test_india_seed_file_valid(self) -> None:
        seed_file = Path(__file__).resolve().parent.parent.parent.parent / "seeds" / "market_config_IN.json"
        data = json.loads(seed_file.read_text(encoding="utf-8"))
        assert data["region_code"] == "IN"
        assert data["region_name"] == "India"
        assert "compensation_structure" in data
        assert data["compensation_structure"]["currency_code"] == "INR"

    def test_us_seed_file_valid(self) -> None:
        seed_file = Path(__file__).resolve().parent.parent.parent.parent / "seeds" / "market_config_US.json"
        data = json.loads(seed_file.read_text(encoding="utf-8"))
        assert data["region_code"] == "US"
        assert data["region_name"] == "United States"
        assert data["compensation_structure"]["currency_code"] == "USD"

    def test_seed_files_have_required_fields(self) -> None:
        seeds_dir = Path(__file__).resolve().parent.parent.parent.parent / "seeds"
        for seed_file in seeds_dir.glob("market_config_*.json"):
            data = json.loads(seed_file.read_text(encoding="utf-8"))
            assert "region_code" in data, f"{seed_file.name} missing region_code"
            assert len(data["region_code"]) == 2, f"{seed_file.name} invalid region_code"
