"""Output formatting for raspilapse overlay integration."""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class OverlayOutput:
    """
    Manages combined overlay output from multiple data providers.

    Features:
    - Combines output from multiple providers
    - Handles persistence (items stay visible for configurable time)
    - Clears stale data on startup
    """

    def __init__(
        self,
        data_dir: str | Path,
        stale_minutes: int = 5,
    ):
        """
        Initialize overlay output manager.

        Args:
            data_dir: Directory to write output files
            stale_minutes: Consider data stale if older than this (default: 5)
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.stale_seconds = stale_minutes * 60

        # Clear stale data on startup
        self._startup_cleanup()

    def _startup_cleanup(self) -> None:
        """Clear stale data files on startup."""
        for json_file in self.data_dir.glob("*_current.json"):
            try:
                with open(json_file) as f:
                    data = json.load(f)

                updated_at = data.get("updated_at")
                if updated_at:
                    try:
                        updated_time = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                        age_seconds = (datetime.now(timezone.utc) - updated_time).total_seconds()

                        if age_seconds > self.stale_seconds:
                            logger.info(f"Clearing stale data from {json_file.name} (age: {age_seconds:.0f}s)")
                            self._write_empty(json_file)
                    except (ValueError, TypeError):
                        self._write_empty(json_file)
            except (json.JSONDecodeError, FileNotFoundError):
                pass

    def _write_empty(self, filepath: Path) -> None:
        """Write an empty data file."""
        empty_data = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "count": 0,
            "items": [],
        }
        with open(filepath, "w") as f:
            json.dump(empty_data, f, indent=2)

    def write_provider_data(
        self,
        provider_name: str,
        items: List[Dict[str, Any]],
        overlay_lines: List[str],
    ) -> None:
        """
        Write data from a provider to output files.

        Args:
            provider_name: Name of the provider (e.g., "ships", "aurora")
            items: List of data items (for JSON output)
            overlay_lines: List of formatted text lines (for overlay)
        """
        # Write JSON data
        output = {
            "provider": provider_name,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "count": len(items),
            "items": items,
        }

        json_file = self.data_dir / f"{provider_name}_current.json"
        with open(json_file, "w") as f:
            json.dump(output, f, indent=2)

        # Write text overlay
        text_file = self.data_dir / f"{provider_name}_overlay.txt"
        with open(text_file, "w") as f:
            f.write("\n".join(overlay_lines) if overlay_lines else "")

        logger.debug(f"Wrote {len(items)} items to {json_file.name}")

    def write_combined_overlay(self, provider_data: Dict[str, List[str]]) -> None:
        """
        Write combined overlay from all providers.

        Args:
            provider_data: Dict mapping provider names to overlay lines
        """
        all_lines = []
        for provider_name, lines in provider_data.items():
            if lines:
                all_lines.extend(lines)

        combined_file = self.data_dir / "combined_overlay.txt"
        with open(combined_file, "w") as f:
            f.write("\n".join(all_lines) if all_lines else "No data")

        logger.debug(f"Wrote combined overlay with {len(all_lines)} lines")
