"""Tests for Aurora provider."""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from providers.aurora.provider import AuroraProvider
from providers.aurora.client import AuroraClient


class TestAuroraProvider:
    """Test Aurora provider."""

    @pytest.fixture
    def provider_config(self, tmp_path):
        """Test provider configuration with temp directory."""
        return {
            "enabled": True,
            "api_url": "https://ekstremedia.no/api/pi/aurora",
            "cache_file": "aurora.json",
            "cache_minutes": 5,
        }

    @pytest.fixture
    def provider(self, provider_config, tmp_path):
        """Create provider with temp directory."""
        return AuroraProvider(provider_config, data_dir=tmp_path)

    @pytest.mark.unit
    def test_provider_init(self, provider):
        """Test provider initialization."""
        assert provider.name == "aurora"
        assert provider.enabled is True

    @pytest.mark.unit
    def test_provider_disabled(self, tmp_path):
        """Test disabled provider."""
        config = {"enabled": False}
        provider = AuroraProvider(config, data_dir=tmp_path)

        assert provider.enabled is False

    @pytest.mark.unit
    def test_fetch_returns_empty_when_disabled(self, tmp_path):
        """Test fetch returns empty list when disabled."""
        config = {"enabled": False}
        provider = AuroraProvider(config, data_dir=tmp_path)
        result = provider.fetch()

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.unit
    def test_fetch_returns_empty_when_no_data(self, provider):
        """Test fetch returns empty list when client returns None."""
        with patch.object(provider.client, "get_aurora_data", return_value=None):
            result = provider.fetch()

            assert isinstance(result, list)
            assert len(result) == 0

    @pytest.mark.unit
    def test_fetch_returns_data(self, provider):
        """Test fetch returns transformed data."""
        mock_data = {
            "kp": 3.5,
            "bz": -2.1,
            "bz_status": "south",
            "speed": 450,
            "storm": "G1",
            "conditions": "Good conditions",
            "favorable": True,
            "generated_at": "2026-01-18T10:00:00+00:00",
        }
        with patch.object(provider.client, "get_aurora_data", return_value=mock_data):
            result = provider.fetch()

            assert len(result) == 1
            assert result[0]["kp"] == 3.5
            assert result[0]["bz"] == -2.1
            assert result[0]["bz_status"] == "south"
            assert result[0]["speed"] == 450
            assert result[0]["storm"] == "G1"

    @pytest.mark.unit
    def test_format_for_overlay_empty(self, provider):
        """Test format_for_overlay with empty items."""
        result = provider.format_for_overlay([])

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.unit
    def test_format_for_overlay_with_data(self, provider):
        """Test format_for_overlay with aurora data."""
        items = [
            {"kp": 5, "bz": -3.2, "bz_status": "south", "speed": 500, "storm": "G2"},
            {"kp": 3, "bz": 1.5, "bz_status": "north", "speed": 350, "storm": "G0"},
        ]

        result = provider.format_for_overlay(items)

        assert len(result) == 2
        assert "Aurora: Kp 5, Bz -3.2↓, G2, 500 km/s" == result[0]
        assert "Aurora: Kp 3, Bz 1.5↑, G0, 350 km/s" == result[1]

    @pytest.mark.unit
    def test_format_for_overlay_bz_arrows(self, provider):
        """Test Bz arrow directions in format_for_overlay."""
        # South = down arrow (good for aurora)
        south_item = [
            {"kp": 2, "bz": -1, "bz_status": "south", "speed": 400, "storm": "G0"}
        ]
        result = provider.format_for_overlay(south_item)
        assert "↓" in result[0]

        # North = up arrow
        north_item = [
            {"kp": 2, "bz": 1, "bz_status": "north", "speed": 400, "storm": "G0"}
        ]
        result = provider.format_for_overlay(north_item)
        assert "↑" in result[0]

    @pytest.mark.unit
    def test_get_overlay_text_disabled(self, tmp_path):
        """Test get_overlay_text when disabled."""
        config = {"enabled": False}
        provider = AuroraProvider(config, data_dir=tmp_path)

        result = provider.get_overlay_text()

        assert result == ""

    @pytest.mark.unit
    def test_get_overlay_text_enabled_no_data(self, provider):
        """Test get_overlay_text when enabled but no data."""
        with patch.object(provider.client, "get_aurora_data", return_value=None):
            result = provider.get_overlay_text()

            assert result == ""

    @pytest.mark.unit
    def test_get_overlay_text_enabled_with_data(self, provider):
        """Test get_overlay_text when enabled with data."""
        mock_data = {
            "kp": 4.0,
            "bz": -2.5,
            "bz_status": "south",
            "speed": 500,
            "storm": "G1",
            "conditions": "Active",
            "favorable": True,
            "generated_at": "2026-01-18T10:00:00+00:00",
        }
        with patch.object(provider.client, "get_aurora_data", return_value=mock_data):
            result = provider.get_overlay_text()

            assert "Aurora: Kp 4.0" in result
            assert "Bz -2.5↓" in result
            assert "G1" in result
            assert "500 km/s" in result

    @pytest.mark.unit
    def test_is_enabled(self, provider, tmp_path):
        """Test is_enabled method."""
        assert provider.is_enabled() is True

        disabled_provider = AuroraProvider({"enabled": False}, data_dir=tmp_path)
        assert disabled_provider.is_enabled() is False

    @pytest.mark.unit
    def test_transform_aurora_data(self, provider):
        """Test _transform_aurora_data."""
        raw_data = {
            "kp": 2.3,
            "bz": -0.5,
            "bz_status": "weak_south",
            "speed": 450,
            "storm": "G0",
            "conditions": "Quiet",
            "favorable": False,
            "generated_at": "2026-01-18T12:00:00+00:00",
        }

        result = provider._transform_aurora_data(raw_data)

        assert result["kp"] == 2.3
        assert result["bz"] == -0.5
        assert result["bz_status"] == "weak_south"
        assert result["speed"] == 450
        assert result["storm"] == "G0"
        assert result["favorable"] is False

    @pytest.mark.unit
    def test_transform_aurora_data_missing_fields(self, provider):
        """Test _transform_aurora_data with missing fields uses defaults."""
        raw_data = {"kp": 1.5}

        result = provider._transform_aurora_data(raw_data)

        assert result["kp"] == 1.5
        assert result["bz"] == 0
        assert result["bz_status"] == "unknown"
        assert result["speed"] == 0
        assert result["storm"] == "G0"


class TestAuroraClient:
    """Test Aurora client."""

    @pytest.fixture
    def client(self, tmp_path):
        """Create client with temp cache file."""
        cache_file = tmp_path / "aurora.json"
        return AuroraClient(
            api_url="https://ekstremedia.no/api/pi/aurora",
            cache_file=cache_file,
            cache_minutes=5,
        )

    @pytest.mark.unit
    def test_client_init(self, client):
        """Test client initialization."""
        assert client.api_url == "https://ekstremedia.no/api/pi/aurora"
        assert client.cache_minutes == 5

    @pytest.mark.unit
    def test_cache_validity_no_file(self, client):
        """Test cache validity when no file exists."""
        assert client._is_cache_valid() is False

    @pytest.mark.unit
    def test_cache_validity_fresh(self, client, tmp_path):
        """Test cache validity with fresh cache."""
        import json
        from datetime import datetime, timezone

        cache_data = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "aurora_data": {"kp": 2.0},
        }
        client.cache_file.write_text(json.dumps(cache_data))

        assert client._is_cache_valid() is True

    @pytest.mark.unit
    def test_cache_validity_expired(self, client, tmp_path):
        """Test cache validity with expired cache."""
        import json
        from datetime import datetime, timezone, timedelta

        old_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        cache_data = {
            "fetched_at": old_time.isoformat(),
            "aurora_data": {"kp": 2.0},
        }
        client.cache_file.write_text(json.dumps(cache_data))

        assert client._is_cache_valid() is False

    @pytest.mark.unit
    def test_get_aurora_data_uses_cache(self, client):
        """Test get_aurora_data returns cached data when valid."""
        import json
        from datetime import datetime, timezone

        cached_data = {"kp": 3.0, "bz": -1.0}
        cache_content = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "aurora_data": cached_data,
        }
        client.cache_file.write_text(json.dumps(cache_content))

        result = client.get_aurora_data()

        assert result == cached_data

    @pytest.mark.unit
    def test_get_aurora_data_force_refresh(self, client):
        """Test get_aurora_data with force_refresh fetches new data."""
        import json
        from datetime import datetime, timezone

        # Write valid cache
        cache_content = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "aurora_data": {"kp": 2.0},
        }
        client.cache_file.write_text(json.dumps(cache_content))

        # Mock API response
        new_data = {"kp": 5.0, "bz": -3.0}
        with patch.object(client, "_fetch_from_api", return_value=new_data):
            result = client.get_aurora_data(force_refresh=True)

            assert result == new_data

    @pytest.mark.unit
    def test_get_aurora_data_fallback_to_stale_cache(self, client):
        """Test get_aurora_data falls back to stale cache on API failure."""
        import json
        from datetime import datetime, timezone, timedelta

        # Write expired cache
        old_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        stale_data = {"kp": 1.5}
        cache_content = {
            "fetched_at": old_time.isoformat(),
            "aurora_data": stale_data,
        }
        client.cache_file.write_text(json.dumps(cache_content))

        # Mock API failure
        with patch.object(client, "_fetch_from_api", return_value=None):
            result = client.get_aurora_data()

            assert result == stale_data

    @pytest.mark.unit
    def test_fetch_from_api_success(self, client):
        """Test _fetch_from_api with successful response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"kp": 4.0, "bz": -2.0}

        with patch.object(client.session, "get", return_value=mock_response):
            result = client._fetch_from_api()

            assert result["kp"] == 4.0
            assert result["bz"] == -2.0

    @pytest.mark.unit
    def test_fetch_from_api_failure(self, client):
        """Test _fetch_from_api with failed response."""
        import requests as req

        with patch.object(
            client.session, "get", side_effect=req.RequestException("Server error")
        ):
            result = client._fetch_from_api()

            assert result is None
