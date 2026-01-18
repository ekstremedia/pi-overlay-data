"""Tests for Aurora provider."""

import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from providers.aurora.provider import AuroraProvider


class TestAuroraProvider:
    """Test Aurora provider."""

    @pytest.fixture
    def provider_config(self):
        """Test provider configuration."""
        return {
            "enabled": True,
        }

    @pytest.mark.unit
    def test_provider_init(self, provider_config):
        """Test provider initialization."""
        provider = AuroraProvider(provider_config)

        assert provider.name == "aurora"
        assert provider.enabled is True

    @pytest.mark.unit
    def test_provider_disabled(self):
        """Test disabled provider."""
        config = {"enabled": False}
        provider = AuroraProvider(config)

        assert provider.enabled is False

    @pytest.mark.unit
    def test_fetch_returns_empty_list(self, provider_config):
        """Test fetch returns empty list (not yet implemented)."""
        provider = AuroraProvider(provider_config)
        result = provider.fetch()

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.unit
    def test_format_for_overlay_empty(self, provider_config):
        """Test format_for_overlay with empty items."""
        provider = AuroraProvider(provider_config)
        result = provider.format_for_overlay([])

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.unit
    def test_format_for_overlay_with_data(self, provider_config):
        """Test format_for_overlay with aurora data."""
        provider = AuroraProvider(provider_config)
        items = [
            {"kp_index": 5, "activity": "high activity"},
            {"kp_index": 3, "activity": "moderate activity"},
        ]

        result = provider.format_for_overlay(items)

        assert len(result) == 2
        assert "Aurora: Kp 5, high activity" in result[0]
        assert "Aurora: Kp 3, moderate activity" in result[1]

    @pytest.mark.unit
    def test_get_overlay_text_disabled(self):
        """Test get_overlay_text when disabled."""
        config = {"enabled": False}
        provider = AuroraProvider(config)

        result = provider.get_overlay_text()

        assert result == ""

    @pytest.mark.unit
    def test_get_overlay_text_enabled(self, provider_config):
        """Test get_overlay_text when enabled (returns empty since no API)."""
        provider = AuroraProvider(provider_config)

        result = provider.get_overlay_text()

        # Returns empty since fetch() returns []
        assert result == ""

    @pytest.mark.unit
    def test_is_enabled(self, provider_config):
        """Test is_enabled method."""
        provider = AuroraProvider(provider_config)
        assert provider.is_enabled() is True

        disabled_provider = AuroraProvider({"enabled": False})
        assert disabled_provider.is_enabled() is False
