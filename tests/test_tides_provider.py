"""Tests for Tides provider."""

import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from providers.tides.provider import TidesProvider


class TestTidesProvider:
    """Test Tides provider."""

    @pytest.fixture
    def provider_config(self):
        """Test provider configuration."""
        return {
            "enabled": True,
        }

    @pytest.mark.unit
    def test_provider_init(self, provider_config):
        """Test provider initialization."""
        provider = TidesProvider(provider_config)

        assert provider.name == "tides"
        assert provider.enabled is True

    @pytest.mark.unit
    def test_provider_disabled(self):
        """Test disabled provider."""
        config = {"enabled": False}
        provider = TidesProvider(config)

        assert provider.enabled is False

    @pytest.mark.unit
    def test_fetch_returns_empty_list(self, provider_config):
        """Test fetch returns empty list (not yet implemented)."""
        provider = TidesProvider(provider_config)
        result = provider.fetch()

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.unit
    def test_format_for_overlay_empty(self, provider_config):
        """Test format_for_overlay with empty items."""
        provider = TidesProvider(provider_config)
        result = provider.format_for_overlay([])

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.unit
    def test_format_for_overlay_with_data(self, provider_config):
        """Test format_for_overlay with tide data."""
        provider = TidesProvider(provider_config)
        items = [
            {"level": 1.5, "trend": "rising", "next_event": "high at 14:30"},
            {"level": 0.3, "trend": "falling", "next_event": "low at 20:45"},
        ]

        result = provider.format_for_overlay(items)

        assert len(result) == 2
        assert "Tide: 1.5m, rising (high at 14:30)" in result[0]
        assert "Tide: 0.3m, falling (low at 20:45)" in result[1]

    @pytest.mark.unit
    def test_format_for_overlay_decimal_formatting(self, provider_config):
        """Test that level is formatted with one decimal place."""
        provider = TidesProvider(provider_config)
        items = [
            {"level": 1.234, "trend": "rising", "next_event": ""},
        ]

        result = provider.format_for_overlay(items)

        assert "1.2m" in result[0]

    @pytest.mark.unit
    def test_get_overlay_text_disabled(self):
        """Test get_overlay_text when disabled."""
        config = {"enabled": False}
        provider = TidesProvider(config)

        result = provider.get_overlay_text()

        assert result == ""

    @pytest.mark.unit
    def test_get_overlay_text_enabled(self, provider_config):
        """Test get_overlay_text when enabled (returns empty since no API)."""
        provider = TidesProvider(provider_config)

        result = provider.get_overlay_text()

        # Returns empty since fetch() returns []
        assert result == ""

    @pytest.mark.unit
    def test_is_enabled(self, provider_config):
        """Test is_enabled method."""
        provider = TidesProvider(provider_config)
        assert provider.is_enabled() is True

        disabled_provider = TidesProvider({"enabled": False})
        assert disabled_provider.is_enabled() is False
