"""Tests for base provider module."""

import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.base_provider import BaseProvider


class ConcreteProvider(BaseProvider):
    """Concrete implementation of BaseProvider for testing."""

    name = "test_provider"

    def __init__(self, config, fetch_data=None, should_raise=False):
        super().__init__(config)
        self._fetch_data = fetch_data or []
        self._should_raise = should_raise

    def fetch(self):
        if self._should_raise:
            raise ValueError("Test error")
        return self._fetch_data

    def format_for_overlay(self, items):
        return [f"Item: {item.get('name', 'unknown')}" for item in items]


class TestBaseProvider:
    """Test BaseProvider abstract class."""

    @pytest.mark.unit
    def test_init_with_enabled_true(self):
        """Test provider initialization with enabled=True."""
        config = {"enabled": True, "other_setting": "value"}
        provider = ConcreteProvider(config)

        assert provider.enabled is True
        assert provider.config == config

    @pytest.mark.unit
    def test_init_with_enabled_false(self):
        """Test provider initialization with enabled=False."""
        config = {"enabled": False}
        provider = ConcreteProvider(config)

        assert provider.enabled is False

    @pytest.mark.unit
    def test_init_default_enabled(self):
        """Test provider defaults to enabled=True."""
        config = {}
        provider = ConcreteProvider(config)

        assert provider.enabled is True

    @pytest.mark.unit
    def test_is_enabled_method(self):
        """Test is_enabled method."""
        enabled_provider = ConcreteProvider({"enabled": True})
        disabled_provider = ConcreteProvider({"enabled": False})

        assert enabled_provider.is_enabled() is True
        assert disabled_provider.is_enabled() is False

    @pytest.mark.unit
    def test_get_overlay_text_enabled(self):
        """Test get_overlay_text when provider is enabled."""
        data = [{"name": "Ship A"}, {"name": "Ship B"}]
        provider = ConcreteProvider({"enabled": True}, fetch_data=data)

        result = provider.get_overlay_text()

        assert "Item: Ship A" in result
        assert "Item: Ship B" in result

    @pytest.mark.unit
    def test_get_overlay_text_disabled(self):
        """Test get_overlay_text when provider is disabled."""
        data = [{"name": "Ship A"}]
        provider = ConcreteProvider({"enabled": False}, fetch_data=data)

        result = provider.get_overlay_text()

        assert result == ""

    @pytest.mark.unit
    def test_get_overlay_text_empty_data(self):
        """Test get_overlay_text with no data."""
        provider = ConcreteProvider({"enabled": True}, fetch_data=[])

        result = provider.get_overlay_text()

        assert result == ""

    @pytest.mark.unit
    def test_get_overlay_text_exception_handling(self):
        """Test get_overlay_text handles exceptions gracefully."""
        provider = ConcreteProvider({"enabled": True}, should_raise=True)

        result = provider.get_overlay_text()

        assert "test_provider: error" in result

    @pytest.mark.unit
    def test_provider_name(self):
        """Test provider name attribute."""
        provider = ConcreteProvider({"enabled": True})

        assert provider.name == "test_provider"

    @pytest.mark.unit
    def test_format_for_overlay_multiline(self):
        """Test that get_overlay_text joins lines correctly."""
        data = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
        provider = ConcreteProvider({"enabled": True}, fetch_data=data)

        result = provider.get_overlay_text()
        lines = result.split("\n")

        assert len(lines) == 3
        assert lines[0] == "Item: A"
        assert lines[1] == "Item: B"
        assert lines[2] == "Item: C"


class TestBaseProviderAbstract:
    """Test that BaseProvider is properly abstract."""

    @pytest.mark.unit
    def test_cannot_instantiate_directly(self):
        """Test that BaseProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseProvider({})

    @pytest.mark.unit
    def test_subclass_must_implement_fetch(self):
        """Test that subclass must implement fetch method."""

        class IncompleteProvider(BaseProvider):
            name = "incomplete"

            def format_for_overlay(self, items):
                return []

        with pytest.raises(TypeError):
            IncompleteProvider({})

    @pytest.mark.unit
    def test_subclass_must_implement_format_for_overlay(self):
        """Test that subclass must implement format_for_overlay method."""

        class IncompleteProvider(BaseProvider):
            name = "incomplete"

            def fetch(self):
                return []

        with pytest.raises(TypeError):
            IncompleteProvider({})
