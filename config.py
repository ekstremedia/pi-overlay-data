"""Configuration handling for pi-overlay-data."""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def load_geojson_polygon(geojson_path: Path) -> List[List[float]]:
    """
    Load polygon coordinates from a GeoJSON file.

    Args:
        geojson_path: Path to the GeoJSON file

    Returns:
        List of [lon, lat] coordinates forming the polygon
    """
    with open(geojson_path) as f:
        data = json.load(f)

    # Handle FeatureCollection
    if data.get("type") == "FeatureCollection":
        features = data.get("features", [])
        if not features:
            raise ValueError(f"No features in GeoJSON: {geojson_path}")
        geometry = features[0].get("geometry", {})
    # Handle single Feature
    elif data.get("type") == "Feature":
        geometry = data.get("geometry", {})
    # Handle raw geometry
    else:
        geometry = data

    geom_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])

    if geom_type == "Polygon":
        # Polygon coordinates are wrapped in an extra array (outer ring)
        return coordinates[0] if coordinates else []
    elif geom_type == "LineString":
        # LineString can be used directly, but ensure it's closed
        if coordinates and coordinates[0] != coordinates[-1]:
            coordinates = coordinates + [coordinates[0]]
        return coordinates
    else:
        raise ValueError(f"Unsupported geometry type: {geom_type}")


class Config:
    """Configuration manager for pi-overlay-data."""

    def __init__(self, env_path: Optional[str] = None, config_path: Optional[str] = None):
        """
        Initialize configuration.

        Args:
            env_path: Path to .env file
            config_path: Path to zone.json file (geojson)
        """
        self._load_env(env_path)
        self._config_path = config_path
        self._polygon: List[List[float]] = []

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
        Load zone configuration from GeoJSON file.

        Args:
            config_path: Path to zone.json file
        """
        path = config_path or self._config_path

        if path:
            geojson_file = Path(path)
        else:
            # Default location: geojson/zone.json
            search_paths = [
                Path.cwd() / "geojson" / "zone.json",
                Path(__file__).parent / "geojson" / "zone.json",
            ]

            geojson_file = None
            for p in search_paths:
                if p.exists():
                    geojson_file = p
                    break

        if geojson_file and geojson_file.exists():
            try:
                self._polygon = load_geojson_polygon(geojson_file)
                logger.info(f"Loaded zone from {geojson_file}")

                # Create a single zone from the geojson
                self.barentswatch["zones"] = [
                    {
                        "id": "default",
                        "name": "Default Zone",
                        "polygon": self._polygon,
                    }
                ]
            except Exception as e:
                logger.error(f"Failed to load zone from {geojson_file}: {e}")
        else:
            logger.warning("No zone.json found in geojson/ directory")

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

    @property
    def polygon(self) -> List[List[float]]:
        """Get the configured polygon."""
        return self._polygon

    def get_zone(self, zone_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific zone by ID."""
        for zone in self.zones:
            if zone.get("id") == zone_id:
                return zone
        return None
