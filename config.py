"""Configuration handling for pi-overlay-data."""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for pi-overlay-data."""

    def __init__(self, env_path: Optional[str] = None, config_path: Optional[str] = None):
        """
        Initialize configuration.

        Args:
            env_path: Path to .env file
            config_path: Path to config.json file
        """
        self._load_env(env_path)
        self._config: Dict[str, Any] = {}
        self._config_path = config_path

        # Global settings
        self.data_dir = os.getenv("DATA_DIR", str(Path(__file__).parent / "data"))
        self.cache_duration = int(os.getenv("CACHE_DURATION", "60"))

        # Barentswatch settings
        self.barentswatch = {
            "enabled": os.getenv("BARENTSWATCH_ENABLED", "true").lower() == "true",
            "client_id": os.getenv("BARENTSWATCH_CLIENT_ID", ""),
            "client_secret": os.getenv("BARENTSWATCH_CLIENT_SECRET", ""),
            "lookback_hours": int(os.getenv("LOOKBACK_HOURS", "3")),
            "persist_minutes": int(os.getenv("PERSIST_MINUTES", "10")),
            "zones": [],
        }

        # Aurora settings (placeholder)
        self.aurora = {
            "enabled": os.getenv("AURORA_ENABLED", "false").lower() == "true",
        }

        # Tides settings (placeholder)
        self.tides = {
            "enabled": os.getenv("TIDES_ENABLED", "false").lower() == "true",
        }

    def _load_env(self, env_path: Optional[str] = None) -> None:
        """Load environment variables from .env file."""
        if env_path:
            load_dotenv(env_path)
            return

        search_paths = [
            Path.cwd() / ".env",
            Path(__file__).parent / ".env",
        ]

        for path in search_paths:
            if path.exists():
                load_dotenv(path)
                logger.debug(f"Loaded .env from {path}")
                return

    def load_config(self, config_path: Optional[str] = None) -> None:
        """
        Load configuration from JSON file.

        Args:
            config_path: Path to config.json file
        """
        path = config_path or self._config_path

        if path:
            config_file = Path(path)
        else:
            search_paths = [
                Path.cwd() / "config" / "config.json",
                Path(__file__).parent / "config" / "config.json",
            ]

            config_file = None
            for p in search_paths:
                if p.exists():
                    config_file = p
                    break

        if config_file and config_file.exists():
            with open(config_file) as f:
                self._config = json.load(f)
                logger.info(f"Loaded config from {config_file}")

            # Load zones into barentswatch config
            if "zones" in self._config:
                self.barentswatch["zones"] = self._config["zones"]

    def get_provider_config(self, provider_name: str) -> Dict[str, Any]:
        """Get configuration for a specific provider."""
        if provider_name == "barentswatch":
            return self.barentswatch
        elif provider_name == "aurora":
            return self.aurora
        elif provider_name == "tides":
            return self.tides
        return {}

    def is_provider_enabled(self, provider_name: str) -> bool:
        """Check if a provider is enabled."""
        config = self.get_provider_config(provider_name)
        return config.get("enabled", False)

    @property
    def zones(self) -> List[Dict[str, Any]]:
        """Get list of configured zones."""
        return self.barentswatch.get("zones", [])

    def get_zone(self, zone_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific zone by ID."""
        for zone in self.zones:
            if zone.get("id") == zone_id:
                return zone
        return None
