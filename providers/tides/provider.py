"""Tide and water level data provider."""

import logging
from typing import Dict, List, Any

from core.base_provider import BaseProvider

logger = logging.getLogger(__name__)


class TidesProvider(BaseProvider):
    """
    Tide and water level provider.

    TODO: Integrate with tide APIs:
    - Kartverket Se Havnivå (Norwegian tide data)
    - NOAA Tides and Currents
    """

    name = "tides"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # TODO: Configure location and API

    def fetch(self) -> List[Dict[str, Any]]:
        """Fetch tide data."""
        # TODO: Implement API integration
        return []

    def format_for_overlay(self, items: List[Dict[str, Any]]) -> List[str]:
        """Format tide data for overlay."""
        if not items:
            return []

        # Example format:
        # "Tide: 1.2m, rising (high at 14:30)"
        lines = []
        for item in items:
            level = item.get("level", 0)
            trend = item.get("trend", "unknown")
            next_event = item.get("next_event", "")
            lines.append(f"Tide: {level:.1f}m, {trend} ({next_event})")

        return lines
