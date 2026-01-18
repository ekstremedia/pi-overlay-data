"""Barentswatch ship tracking provider."""

import logging
import time
from typing import Dict, List, Any, Optional

from core.base_provider import BaseProvider
from core.heading import degrees_to_compass_8point
from .client import BarentswatchClient

logger = logging.getLogger(__name__)


def point_in_polygon(lat: float, lon: float, polygon: List[List[float]]) -> bool:
    """Check if a point is inside a polygon using ray casting algorithm."""
    n = len(polygon)
    inside = False

    j = n - 1
    for i in range(n):
        xi, yi = polygon[i][0], polygon[i][1]
        xj, yj = polygon[j][0], polygon[j][1]

        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i

    return inside


class BarentswatchProvider(BaseProvider):
    """
    Ship tracking provider using Barentswatch AIS API.

    Monitors configured polygon zones for ships and provides
    formatted overlay data with persistence.
    """

    name = "ships"

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Barentswatch provider.

        Args:
            config: Configuration with keys:
                - client_id: Barentswatch OAuth2 client ID
                - client_secret: Barentswatch OAuth2 client secret
                - zones: List of zone configurations
                - lookback_hours: How far back to search (default: 3)
                - persist_minutes: How long to keep ships visible (default: 10)
        """
        super().__init__(config)

        self.client = BarentswatchClient(
            config.get("client_id", ""),
            config.get("client_secret", ""),
        )

        self.zones = config.get("zones", [])
        self.lookback_hours = config.get("lookback_hours", 3)
        self.persist_minutes = config.get("persist_minutes", 10)
        self.persist_seconds = self.persist_minutes * 60

        # Categories to exclude from display (buoys, fishing gear, etc.)
        # Default excludes Unknown category which contains non-vessel AIS transmitters
        self.exclude_categories = config.get("exclude_categories", ["Unknown"])

        # Minimum speed to display (filters out stationary/anchored ships)
        # Default 0.5 kts to ignore drift, set higher to only show moving ships
        self.min_speed = config.get("min_speed", 0.5)

        # Track when ships were last seen: mmsi -> timestamp
        self._last_seen: Dict[int, float] = {}
        # Track ship data: mmsi -> ship info
        self._ships: Dict[int, Dict[str, Any]] = {}

    def fetch(self) -> List[Dict[str, Any]]:
        """
        Fetch ships from Barentswatch API.

        Returns:
            List of ships currently in the zone
        """
        if not self.zones:
            return []

        zone = self.zones[0]
        polygon = zone.get("polygon", [])
        if not polygon:
            logger.error("Zone has no polygon")
            return []

        try:
            # Fetch ships from API
            ships = self.client.get_ships_in_area(
                polygon=polygon,
                lookback_hours=self.lookback_hours,
            )

            # Filter to only ships currently in polygon
            ships_in_zone = []
            for ship in ships:
                lat = ship.get("latitude")
                lon = ship.get("longitude")
                if lat is not None and lon is not None:
                    if point_in_polygon(lat, lon, polygon):
                        ships_in_zone.append(ship)

            logger.info(f"Found {len(ships_in_zone)} ships in zone")
            return ships_in_zone

        except Exception as e:
            logger.error(f"Error fetching ships: {e}")
            return []

    def update(self) -> List[Dict[str, Any]]:
        """
        Fetch ships and update persistence tracking.

        Ships remain visible for persist_minutes after leaving the zone.

        Returns:
            List of ships to display (including recently departed)
        """
        now = time.time()
        current_ships = self.fetch()

        # Update tracking for current ships
        for ship in current_ships:
            mmsi = ship.get("mmsi")
            if mmsi:
                self._last_seen[mmsi] = now
                self._ships[mmsi] = ship

        # Build display list (current + recently seen)
        display_ships = []
        expired = []

        for mmsi, last_seen in self._last_seen.items():
            age = now - last_seen
            if age <= self.persist_seconds:
                ship = self._ships.get(mmsi)
                if ship:
                    formatted = self._format_ship(ship)
                    # Filter out excluded categories (buoys, fishing gear, etc.)
                    if formatted.get("category") in self.exclude_categories:
                        continue
                    # Filter out stationary/slow ships below min_speed
                    if formatted.get("speed", 0) < self.min_speed:
                        continue
                    formatted["seconds_since_seen"] = int(age)
                    formatted["still_in_zone"] = age < 5
                    display_ships.append(formatted)
            else:
                expired.append(mmsi)

        # Clean up expired
        for mmsi in expired:
            del self._last_seen[mmsi]
            if mmsi in self._ships:
                del self._ships[mmsi]

        # Sort by name
        display_ships.sort(key=lambda s: s.get("name", ""))
        return display_ships

    def _format_ship(self, ship: Dict[str, Any]) -> Dict[str, Any]:
        """Format a ship for output."""
        mmsi = ship.get("mmsi", 0)
        name = ship.get("name", "Unknown")
        speed = ship.get("speedOverGround") or 0
        heading = ship.get("trueHeading") or ship.get("courseOverGround")

        direction = degrees_to_compass_8point(heading) if heading is not None else "unknown"

        # Format: NAME (MMSI) 12.2 kts, north-west
        if speed > 0.5:
            display = f"{name} ({mmsi}) {speed:.1f} kts, {direction}"
        else:
            display = f"{name} ({mmsi}) stationary"

        return {
            "mmsi": mmsi,
            "name": name,
            "speed": round(speed, 1),
            "heading": heading,
            "direction": direction,
            "display": display,
            "latitude": ship.get("latitude"),
            "longitude": ship.get("longitude"),
            "ship_type": ship.get("shipTypeString", "Unknown"),
            "category": ship.get("shipCategory", "Unknown"),
        }

    def format_for_overlay(self, items: List[Dict[str, Any]]) -> List[str]:
        """Format ships as overlay text lines."""
        return [item.get("display", "") for item in items]

    def get_overlay_lines(self) -> List[str]:
        """Get formatted overlay lines for the zone."""
        ships = self.update()
        return self.format_for_overlay(ships)

    def clear(self) -> None:
        """Clear all tracked ships."""
        self._last_seen.clear()
        self._ships.clear()
