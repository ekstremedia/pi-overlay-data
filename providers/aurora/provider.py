"""Aurora/Northern Lights forecast provider."""

import logging
from typing import Dict, List, Any

from core.base_provider import BaseProvider

logger = logging.getLogger(__name__)


class AuroraProvider(BaseProvider):
    """
    Aurora forecast provider.

    TODO: Integrate with aurora forecast APIs:
    - NOAA Space Weather Prediction Center
    - Norwegian aurora forecast
    - Yr.no
    """

    name = "aurora"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # TODO: Configure API endpoints and location

    def fetch(self) -> List[Dict[str, Any]]:
        """Fetch aurora forecast data."""
        # TODO: Implement API integration
        return []

    def format_for_overlay(self, items: List[Dict[str, Any]]) -> List[str]:
        """Format aurora data for overlay."""
        if not items:
            return []

        # Example format:
        # "Aurora: Kp 5, high activity"
        lines = []
        for item in items:
            kp = item.get("kp_index", 0)
            activity = item.get("activity", "unknown")
            lines.append(f"Aurora: Kp {kp}, {activity}")

        return lines
