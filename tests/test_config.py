"""Tests for configuration module."""

import pytest
import os
import sys
import json
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import Config


class TestConfig:
    """Test configuration loading."""

    @pytest.mark.unit
    def test_config_defaults(self):
        """Test default configuration values."""
        # Clear env vars that might interfere
        old_env = {}
        for key in ["BARENTSWATCH_CLIENT_ID", "BARENTSWATCH_CLIENT_SECRET"]:
            old_env[key] = os.environ.pop(key, None)

        try:
            config = Config()
            assert config.cache_duration == 60
            assert config.barentswatch["lookback_hours"] == 3
            assert config.barentswatch["persist_minutes"] == 10
        finally:
            # Restore env vars
            for key, value in old_env.items():
                if value is not None:
                    os.environ[key] = value

    @pytest.mark.unit
    def test_config_from_env(self):
        """Test configuration from environment variables."""
        os.environ["BARENTSWATCH_CLIENT_ID"] = "test_id"
        os.environ["BARENTSWATCH_CLIENT_SECRET"] = "test_secret"
        os.environ["CACHE_DURATION"] = "120"

        try:
            config = Config()
            assert config.barentswatch["client_id"] == "test_id"
            assert config.barentswatch["client_secret"] == "test_secret"
            assert config.cache_duration == 120
        finally:
            del os.environ["BARENTSWATCH_CLIENT_ID"]
            del os.environ["BARENTSWATCH_CLIENT_SECRET"]
            del os.environ["CACHE_DURATION"]

    @pytest.mark.unit
    def test_load_config_json(self):
        """Test loading zones from JSON config file."""
        config_data = {
            "zones": [
                {
                    "id": "test_zone",
                    "name": "Test Zone",
                    "polygon": [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]],
                }
            ]
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(config_data, f)
            config_path = f.name

        try:
            config = Config(config_path=config_path)
            config.load_config()

            assert len(config.zones) == 1
            assert config.zones[0]["id"] == "test_zone"
            assert config.get_zone("test_zone") is not None
            assert config.get_zone("nonexistent") is None
        finally:
            os.unlink(config_path)

    @pytest.mark.unit
    def test_provider_enabled_check(self):
        """Test checking if providers are enabled."""
        os.environ["BARENTSWATCH_ENABLED"] = "true"
        os.environ["AURORA_ENABLED"] = "false"

        try:
            config = Config()
            assert config.is_provider_enabled("barentswatch") is True
            assert config.is_provider_enabled("aurora") is False
            assert config.is_provider_enabled("unknown") is False
        finally:
            del os.environ["BARENTSWATCH_ENABLED"]
            del os.environ["AURORA_ENABLED"]

    @pytest.mark.unit
    def test_get_provider_config(self):
        """Test getting provider-specific configuration."""
        config = Config()

        bw_config = config.get_provider_config("barentswatch")
        assert "client_id" in bw_config
        assert "client_secret" in bw_config
        assert "lookback_hours" in bw_config

        aurora_config = config.get_provider_config("aurora")
        assert "enabled" in aurora_config

        unknown_config = config.get_provider_config("unknown")
        assert unknown_config == {}
