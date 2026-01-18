"""Aurora/Northern Lights forecast provider."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.base_provider import BaseProvider
from providers.aurora.client import AuroraClient

logger = logging.getLogger(__name__)


class AuroraProvider(BaseProvider):
    """
    Aurora forecast provider.

    Fetches aurora/space weather data from ekstremedia.no API and caches locally.
    Data includes Kp index, Bz, solar wind speed, and storm level.
    """

    name = "aurora"

    def __init__(self, config: Dict[str, Any], data_dir: Optional[Path] = None):
        """
        Initialize aurora provider.

        Args:
            config: Provider configuration dict
            data_dir: Directory for cache file (defaults to ./data)
        """
        super().__init__(config)

        self.api_url = config.get("api_url", "https://ekstremedia.no/api/pi/aurora")
        self.cache_minutes = config.get("cache_minutes", 5)

        # Determine cache file path
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data"
        cache_filename = config.get("cache_file", "aurora.json")
        self.cache_file = data_dir / cache_filename

        # Initialize client
        self.client = AuroraClient(
            api_url=self.api_url,
            cache_file=self.cache_file,
            cache_minutes=self.cache_minutes,
        )

    def fetch(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Fetch aurora data.

        Args:
            force_refresh: Force fetching fresh data from API

        Returns:
            List containing single aurora data item, or empty list on failure
        """
        if not self.enabled:
            return []

        data = self.client.get_aurora_data(force_refresh=force_refresh)
        if not data:
            logger.warning("No aurora data available")
            return []

        # Transform API response to our format
        item = self._transform_aurora_data(data)
        return [item] if item else []

    def _transform_aurora_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Transform API response to provider format.

        Args:
            data: Raw API response

        Returns:
            Transformed aurora data dict
        """
        try:
            return {
                "kp": data.get("kp", 0),
                "bz": data.get("bz", 0),
                "bz_status": data.get("bz_status", "unknown"),
                "speed": data.get("speed", 0),
                "storm": data.get("storm", "G0"),
                "conditions": data.get("conditions", ""),
                "favorable": data.get("favorable", False),
                "generated_at": data.get("generated_at"),
            }

        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"Failed to transform aurora data: {e}")
            return None

    def format_for_overlay(self, items: List[Dict[str, Any]]) -> List[str]:
        """
        Format aurora data for overlay.

        Args:
            items: List of aurora data items

        Returns:
            List of formatted strings for display
        """
        if not items:
            return []

        lines = []
        for item in items:
            kp = item.get("kp", 0)
            bz = item.get("bz", 0)
            bz_status = item.get("bz_status", "unknown")
            storm = item.get("storm", "G0")
            speed = item.get("speed", 0)

            # Bz arrow: south (↓) is good for aurora, north (↑) is not
            bz_arrow = "↓" if bz_status == "south" else "↑"

            lines.append(f"Aurora: Kp {kp}, Bz {bz}{bz_arrow}, {storm}, {speed} km/s")

        return lines
