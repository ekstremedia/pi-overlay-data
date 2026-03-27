"""Tide and water level data provider."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.base_provider import BaseProvider
from providers.tides.client import TideClient

logger = logging.getLogger(__name__)


class TidesProvider(BaseProvider):
    """
    Tide and water level provider.

    Fetches tide data from ekstremedia.no API and caches locally.
    Data includes current water level, trend, and next high/low times.
    """

    name = "tides"

    def __init__(self, config: Dict[str, Any], data_dir: Optional[Path] = None):
        """
        Initialize tide provider.

        Args:
            config: Provider configuration dict
            data_dir: Directory for cache file (defaults to ./data)
        """
        super().__init__(config)

        self.api_url = config.get("api_url", "https://ekstremedia.no/api/pi/tide")
        self.cache_hours = config.get("cache_hours", 24)

        # Determine cache file path
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data"
        cache_filename = config.get("cache_file", "tide.json")
        self.cache_file = data_dir / cache_filename

        # Initialize client
        self.client = TideClient(
            api_url=self.api_url,
            cache_file=self.cache_file,
            cache_hours=self.cache_hours,
        )

    def fetch(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Fetch tide data.

        Args:
            force_refresh: Force fetching fresh data from API (ignores cache)

        Returns:
            List containing single tide data item, or empty list on failure
        """
        if not self.enabled:
            return []

        data = self.client.get_tide_data(force_refresh=force_refresh)
        if not data:
            logger.warning("No tide data available")
            return []

        # Transform API response to our format
        item = self._transform_tide_data(data)
        return [item] if item else []

    def _transform_tide_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Transform API response to provider format.

        Args:
            data: Raw API response

        Returns:
            Transformed tide data dict
        """
        try:
            # Check if API provides pre-computed values (legacy format)
            current = data.get("current", {})
            next_high = data.get("next_high", {})
            next_low = data.get("next_low", {})

            # If not provided, calculate from points
            points = data.get("points", [])
            if points and not current:
                current, next_high, next_low = self._calculate_from_points(points)

            # Convert cm to meters
            level_cm = current.get("level_cm", 0)
            level_m = level_cm / 100.0

            trend = current.get("trend", "unknown")

            # Determine next event (whichever is sooner)
            next_event = self._get_next_event(next_high, next_low)

            return {
                "location": data.get("location", "Unknown"),
                "level": level_m,
                "level_cm": level_cm,
                "trend": trend,
                "next_event": next_event,
                "next_high": next_high,
                "next_low": next_low,
                "generated_at": data.get("generated_at"),
            }

        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"Failed to transform tide data: {e}")
            return None

    def _calculate_from_points(self, points: List[Dict[str, Any]]) -> tuple:
        """
        Calculate current level, trend, and next high/low from points data.

        Args:
            points: List of points with time and level_cm

        Returns:
            Tuple of (current, next_high, next_low) dicts
        """
        if not points:
            return {}, {}, {}

        now = datetime.now().astimezone()

        # Parse all points with their times
        parsed_points = []
        for p in points:
            try:
                t = datetime.fromisoformat(p["time"])
                parsed_points.append({"time": t, "level_cm": p["level_cm"]})
            except (KeyError, ValueError):
                continue

        if not parsed_points:
            return {}, {}, {}

        # Sort by time
        parsed_points.sort(key=lambda x: x["time"])

        # Find current level (closest point to now, preferring past or equal)
        current_idx = 0
        for i, p in enumerate(parsed_points):
            if p["time"] <= now:
                current_idx = i
            else:
                break

        current_level = parsed_points[current_idx]["level_cm"]

        # Calculate trend by comparing with previous point
        trend = "stable"
        if current_idx > 0:
            prev_level = parsed_points[current_idx - 1]["level_cm"]
            if current_level > prev_level:
                trend = "rising"
            elif current_level < prev_level:
                trend = "falling"

        current = {"level_cm": current_level, "trend": trend}

        # Find next high and low from future points
        next_high = {}
        next_low = {}

        # Look for true extrema in future points using a wider window
        # to avoid detecting noise/plateaus as separate high/low
        future_points = [p for p in parsed_points if p["time"] > now]

        # Find all local extrema first, then pick the significant ones
        all_highs = []
        all_lows = []

        # Use a window of 3 points on each side (30 min with 10-min data)
        # to find robust extrema that aren't just noise
        window = 3
        if len(future_points) >= (2 * window + 1):
            for i in range(window, len(future_points) - window):
                curr_l = future_points[i]["level_cm"]
                curr_t = future_points[i]["time"]

                # Get levels in window before and after
                before = [future_points[j]["level_cm"] for j in range(i - window, i)]
                after = [
                    future_points[j]["level_cm"] for j in range(i + 1, i + window + 1)
                ]

                # Local maximum: current is higher than all points in window
                if all(curr_l >= b for b in before) and all(curr_l >= a for a in after):
                    # Also check it's actually higher than at least some points
                    if curr_l > min(before) and curr_l > min(after):
                        all_highs.append(
                            {
                                "time": curr_t,
                                "level_cm": curr_l,
                            }
                        )

                # Local minimum: current is lower than all points in window
                if all(curr_l <= b for b in before) and all(curr_l <= a for a in after):
                    # Also check it's actually lower than at least some points
                    if curr_l < max(before) and curr_l < max(after):
                        all_lows.append(
                            {
                                "time": curr_t,
                                "level_cm": curr_l,
                            }
                        )

        # Pick the first valid high and low that make sense together
        # They should be at least 3 hours apart and have meaningful height diff
        min_separation_hours = 3
        min_height_diff_cm = 20

        for h in all_highs:
            if next_high:
                break
            for low in all_lows:
                time_diff = abs((h["time"] - low["time"]).total_seconds() / 3600)
                height_diff = abs(h["level_cm"] - low["level_cm"])

                if (
                    time_diff >= min_separation_hours
                    and height_diff >= min_height_diff_cm
                ):
                    next_high = {
                        "time": h["time"].isoformat(),
                        "level_cm": h["level_cm"],
                    }
                    next_low = {
                        "time": low["time"].isoformat(),
                        "level_cm": low["level_cm"],
                    }
                    break

        # Fallback: if validation filtered everything out, use first extrema
        # but only if we have both and they're reasonably separated
        if not next_high and all_highs:
            next_high = {
                "time": all_highs[0]["time"].isoformat(),
                "level_cm": all_highs[0]["level_cm"],
            }
        if not next_low and all_lows:
            next_low = {
                "time": all_lows[0]["time"].isoformat(),
                "level_cm": all_lows[0]["level_cm"],
            }

        return current, next_high, next_low

    def _get_next_event(
        self, next_high: Dict[str, Any], next_low: Dict[str, Any]
    ) -> str:
        """
        Determine the next tide event (high or low).

        Args:
            next_high: Next high tide info
            next_low: Next low tide info

        Returns:
            Formatted string like "high at 14:30" or "low at 20:45"
        """
        try:
            high_time_str = next_high.get("time")
            low_time_str = next_low.get("time")

            if not high_time_str and not low_time_str:
                return ""

            # Parse times
            high_time = None
            low_time = None

            if high_time_str:
                high_time = datetime.fromisoformat(high_time_str)
            if low_time_str:
                low_time = datetime.fromisoformat(low_time_str)

            # Determine which is next
            if high_time and low_time:
                if high_time < low_time:
                    return f"high at {high_time.strftime('%H:%M')}"
                else:
                    return f"low at {low_time.strftime('%H:%M')}"
            elif high_time:
                return f"high at {high_time.strftime('%H:%M')}"
            elif low_time:
                return f"low at {low_time.strftime('%H:%M')}"

            return ""

        except (ValueError, TypeError) as e:
            logger.debug(f"Could not parse tide times: {e}")
            return ""

    def format_for_overlay(self, items: List[Dict[str, Any]]) -> List[str]:
        """
        Format tide data for overlay.

        Args:
            items: List of tide data items

        Returns:
            List of formatted strings for display
        """
        if not items:
            return []

        lines = []
        for item in items:
            level = item.get("level", 0)
            trend = item.get("trend", "unknown")
            next_event = item.get("next_event", "")

            if next_event:
                lines.append(f"Tide: {level:.1f}m, {trend} ({next_event})")
            else:
                lines.append(f"Tide: {level:.1f}m, {trend}")

        return lines
