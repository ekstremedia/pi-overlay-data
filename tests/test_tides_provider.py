"""Tests for Tides provider."""

import json
import pytest
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from providers.tides.provider import TidesProvider
from providers.tides.client import TideClient


class TestTidesProvider:
    """Test Tides provider."""

    @pytest.fixture
    def provider_config(self, tmp_path):
        """Test provider configuration."""
        return {
            "enabled": True,
            "api_url": "https://ekstremedia.no/api/pi/tide",
            "cache_file": "tide.json",
            "cache_hours": 24,
        }

    @pytest.fixture
    def sample_api_response(self):
        """Sample API response from tide endpoint."""
        return {
            "location": "Sortland",
            "generated_at": "2026-01-18T16:07:21+01:00",
            "current": {"level_cm": 150, "trend": "rising"},
            "points": [
                {"time": "2026-01-18T16:00:00+01:00", "level_cm": 150},
                {"time": "2026-01-18T17:00:00+01:00", "level_cm": 160},
            ],
            "next_high": {"time": "2026-01-18T18:30:00+01:00", "level_cm": 180},
            "next_low": {"time": "2026-01-19T00:45:00+01:00", "level_cm": 30},
        }

    @pytest.mark.unit
    def test_provider_init(self, provider_config, tmp_path):
        """Test provider initialization."""
        provider = TidesProvider(provider_config, tmp_path)

        assert provider.name == "tides"
        assert provider.enabled is True
        assert provider.api_url == "https://ekstremedia.no/api/pi/tide"
        assert provider.cache_hours == 24

    @pytest.mark.unit
    def test_provider_disabled(self, tmp_path):
        """Test disabled provider."""
        config = {"enabled": False}
        provider = TidesProvider(config, tmp_path)

        assert provider.enabled is False

    @pytest.mark.unit
    def test_fetch_disabled_returns_empty(self, tmp_path):
        """Test fetch returns empty list when disabled."""
        config = {"enabled": False}
        provider = TidesProvider(config, tmp_path)
        result = provider.fetch()

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.unit
    def test_transform_tide_data(self, provider_config, sample_api_response, tmp_path):
        """Test transformation of API response to provider format."""
        provider = TidesProvider(provider_config, tmp_path)
        result = provider._transform_tide_data(sample_api_response)

        assert result is not None
        assert result["location"] == "Sortland"
        assert result["level"] == 1.5  # 150cm -> 1.5m
        assert result["level_cm"] == 150
        assert result["trend"] == "rising"
        assert result["next_event"] == "high at 18:30"

    @pytest.mark.unit
    def test_get_next_event_high_first(self, provider_config, tmp_path):
        """Test next event when high tide is sooner."""
        provider = TidesProvider(provider_config, tmp_path)

        next_high = {"time": "2026-01-18T14:30:00+01:00", "level_cm": 180}
        next_low = {"time": "2026-01-18T20:45:00+01:00", "level_cm": 30}

        result = provider._get_next_event(next_high, next_low)
        assert result == "high at 14:30"

    @pytest.mark.unit
    def test_get_next_event_low_first(self, provider_config, tmp_path):
        """Test next event when low tide is sooner."""
        provider = TidesProvider(provider_config, tmp_path)

        next_high = {"time": "2026-01-18T20:30:00+01:00", "level_cm": 180}
        next_low = {"time": "2026-01-18T14:45:00+01:00", "level_cm": 30}

        result = provider._get_next_event(next_high, next_low)
        assert result == "low at 14:45"

    @pytest.mark.unit
    def test_get_next_event_empty(self, provider_config, tmp_path):
        """Test next event with no data."""
        provider = TidesProvider(provider_config, tmp_path)
        result = provider._get_next_event({}, {})
        assert result == ""

    @pytest.mark.unit
    def test_format_for_overlay_empty(self, provider_config, tmp_path):
        """Test format_for_overlay with empty items."""
        provider = TidesProvider(provider_config, tmp_path)
        result = provider.format_for_overlay([])

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.unit
    def test_format_for_overlay_with_data(self, provider_config, tmp_path):
        """Test format_for_overlay with tide data."""
        provider = TidesProvider(provider_config, tmp_path)
        items = [
            {"level": 1.5, "trend": "rising", "next_event": "high at 14:30"},
        ]

        result = provider.format_for_overlay(items)

        assert len(result) == 1
        assert result[0] == "Tide: 1.5m, rising (high at 14:30)"

    @pytest.mark.unit
    def test_format_for_overlay_no_next_event(self, provider_config, tmp_path):
        """Test format_for_overlay when next_event is empty."""
        provider = TidesProvider(provider_config, tmp_path)
        items = [
            {"level": 0.3, "trend": "falling", "next_event": ""},
        ]

        result = provider.format_for_overlay(items)

        assert len(result) == 1
        assert result[0] == "Tide: 0.3m, falling"

    @pytest.mark.unit
    def test_format_for_overlay_decimal_formatting(self, provider_config, tmp_path):
        """Test that level is formatted with one decimal place."""
        provider = TidesProvider(provider_config, tmp_path)
        items = [
            {"level": 1.234, "trend": "rising", "next_event": ""},
        ]

        result = provider.format_for_overlay(items)

        assert "1.2m" in result[0]

    @pytest.mark.unit
    def test_get_overlay_text_disabled(self, tmp_path):
        """Test get_overlay_text when disabled."""
        config = {"enabled": False}
        provider = TidesProvider(config, tmp_path)

        result = provider.get_overlay_text()

        assert result == ""

    @pytest.mark.unit
    def test_is_enabled(self, provider_config, tmp_path):
        """Test is_enabled method."""
        provider = TidesProvider(provider_config, tmp_path)
        assert provider.is_enabled() is True

        disabled_provider = TidesProvider({"enabled": False}, tmp_path)
        assert disabled_provider.is_enabled() is False

    @pytest.mark.unit
    def test_fetch_with_mocked_client(
        self, provider_config, sample_api_response, tmp_path
    ):
        """Test fetch with mocked client response."""
        provider = TidesProvider(provider_config, tmp_path)

        # Mock the client's get_tide_data method
        provider.client.get_tide_data = Mock(return_value=sample_api_response)

        result = provider.fetch()

        assert len(result) == 1
        assert result[0]["location"] == "Sortland"
        assert result[0]["level"] == 1.5
        assert result[0]["trend"] == "rising"

    @pytest.mark.unit
    def test_fetch_with_no_data(self, provider_config, tmp_path):
        """Test fetch when client returns None."""
        provider = TidesProvider(provider_config, tmp_path)
        provider.client.get_tide_data = Mock(return_value=None)

        result = provider.fetch()

        assert result == []


class TestTideClient:
    """Test Tide client."""

    @pytest.fixture
    def client(self, tmp_path):
        """Create test client."""
        cache_file = tmp_path / "tide.json"
        return TideClient(
            api_url="https://ekstremedia.no/api/pi/tide",
            cache_file=cache_file,
            cache_hours=24,
        )

    @pytest.fixture
    def sample_api_response(self):
        """Sample API response."""
        return {
            "location": "Sortland",
            "generated_at": "2026-01-18T16:07:21+01:00",
            "current": {"level_cm": 150, "trend": "rising"},
            "next_high": {"time": "2026-01-18T18:30:00+01:00", "level_cm": 180},
            "next_low": {"time": "2026-01-19T00:45:00+01:00", "level_cm": 30},
        }

    @pytest.mark.unit
    def test_client_init(self, client, tmp_path):
        """Test client initialization."""
        assert client.api_url == "https://ekstremedia.no/api/pi/tide"
        assert client.cache_hours == 24
        assert client.cache_file == tmp_path / "tide.json"

    @pytest.mark.unit
    def test_cache_validity_no_file(self, client):
        """Test cache validity when file doesn't exist."""
        assert client._is_cache_valid() is False

    @pytest.mark.unit
    def test_cache_validity_fresh(self, client, sample_api_response):
        """Test cache validity with fresh cache."""
        # Write fresh cache
        cache_data = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "tide_data": sample_api_response,
        }
        with open(client.cache_file, "w") as f:
            json.dump(cache_data, f)

        assert client._is_cache_valid() is True

    @pytest.mark.unit
    def test_cache_validity_expired(self, client, sample_api_response):
        """Test cache validity with expired cache."""
        # Write old cache
        old_time = datetime.now(timezone.utc) - timedelta(hours=25)
        cache_data = {
            "fetched_at": old_time.isoformat(),
            "tide_data": sample_api_response,
        }
        with open(client.cache_file, "w") as f:
            json.dump(cache_data, f)

        assert client._is_cache_valid() is False

    @pytest.mark.unit
    def test_save_and_load_cache(self, client, sample_api_response):
        """Test saving and loading cache."""
        client._save_cache(sample_api_response)

        loaded = client._load_cache()
        assert loaded == sample_api_response

    @pytest.mark.unit
    def test_get_tide_data_uses_cache(self, client, sample_api_response):
        """Test that get_tide_data uses valid cache."""
        # Write fresh cache
        cache_data = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "tide_data": sample_api_response,
        }
        with open(client.cache_file, "w") as f:
            json.dump(cache_data, f)

        # Mock the API call - should not be called
        client._fetch_from_api = Mock()

        result = client.get_tide_data()

        assert result == sample_api_response
        client._fetch_from_api.assert_not_called()

    @pytest.mark.unit
    def test_get_tide_data_force_refresh(self, client, sample_api_response):
        """Test that force_refresh bypasses cache."""
        # Write fresh cache
        cache_data = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "tide_data": sample_api_response,
        }
        with open(client.cache_file, "w") as f:
            json.dump(cache_data, f)

        # Mock API call
        new_data = {**sample_api_response, "current": {"level_cm": 200, "trend": "falling"}}
        client._fetch_from_api = Mock(return_value=new_data)

        result = client.get_tide_data(force_refresh=True)

        assert result == new_data
        client._fetch_from_api.assert_called_once()

    @pytest.mark.unit
    def test_get_tide_data_fallback_to_stale_cache(self, client, sample_api_response):
        """Test fallback to stale cache when API fails."""
        # Write old cache
        old_time = datetime.now(timezone.utc) - timedelta(hours=25)
        cache_data = {
            "fetched_at": old_time.isoformat(),
            "tide_data": sample_api_response,
        }
        with open(client.cache_file, "w") as f:
            json.dump(cache_data, f)

        # Mock API failure
        client._fetch_from_api = Mock(return_value=None)

        result = client.get_tide_data()

        # Should return stale cache as fallback
        assert result == sample_api_response

    @pytest.mark.unit
    def test_fetch_from_api_success(self, client, sample_api_response):
        """Test successful API fetch."""
        mock_response = Mock()
        mock_response.json.return_value = sample_api_response
        mock_response.raise_for_status = Mock()

        with patch.object(client.session, "get", return_value=mock_response):
            result = client._fetch_from_api()

        assert result == sample_api_response

    @pytest.mark.unit
    def test_fetch_from_api_failure(self, client):
        """Test API fetch failure."""
        import requests

        with patch.object(
            client.session, "get", side_effect=requests.RequestException("Connection error")
        ):
            result = client._fetch_from_api()

        assert result is None
