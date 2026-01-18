"""Aurora data client with caching."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class AuroraClient:
    """Client for fetching and caching aurora data."""

    def __init__(
        self,
        api_url: str,
        cache_file: Path,
        cache_minutes: int = 5,
    ):
        """
        Initialize aurora client.

        Args:
            api_url: URL to fetch aurora data from
            cache_file: Path to cache file (aurora.json)
            cache_minutes: Minutes before cache expires (default 5)
        """
        self.api_url = api_url
        self.cache_file = cache_file
        self.cache_minutes = cache_minutes
        self.session = requests.Session()

    def _is_cache_valid(self) -> bool:
        """Check if cached data is still valid."""
        if not self.cache_file.exists():
            return False

        try:
            with open(self.cache_file) as f:
                data = json.load(f)

            fetched_at = data.get("fetched_at")
            if not fetched_at:
                return False

            fetched_time = datetime.fromisoformat(fetched_at)
            now = datetime.now(timezone.utc)
            age_minutes = (now - fetched_time).total_seconds() / 60

            if age_minutes < self.cache_minutes:
                logger.debug(f"Cache valid (age: {age_minutes:.1f}m)")
                return True

            logger.debug(f"Cache expired (age: {age_minutes:.1f}m)")
            return False

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Invalid cache file: {e}")
            return False

    def _load_cache(self) -> Optional[Dict[str, Any]]:
        """Load data from cache file."""
        try:
            with open(self.cache_file) as f:
                data = json.load(f)
            return data.get("aurora_data")
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(f"Failed to load cache: {e}")
            return None

    def _save_cache(self, aurora_data: Dict[str, Any]) -> None:
        """Save data to cache file."""
        cache_data = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "aurora_data": aurora_data,
        }

        self.cache_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.cache_file, "w") as f:
            json.dump(cache_data, f, indent=2)

        logger.info(f"Cached aurora data to {self.cache_file}")

    def _fetch_from_api(self) -> Optional[Dict[str, Any]]:
        """Fetch fresh data from API."""
        try:
            logger.info(f"Fetching aurora data from {self.api_url}")
            response = self.session.get(self.api_url, timeout=30)
            response.raise_for_status()

            data = response.json()
            logger.debug(f"Received aurora data: Kp={data.get('kp')}, Bz={data.get('bz')}")
            return data

        except requests.RequestException as e:
            logger.error(f"Failed to fetch aurora data: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {e}")
            return None

    def get_aurora_data(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get aurora data, using cache if valid.

        Args:
            force_refresh: Force fetching fresh data from API

        Returns:
            Aurora data dict or None if unavailable
        """
        # Check cache first (unless forcing refresh)
        if not force_refresh and self._is_cache_valid():
            cached = self._load_cache()
            if cached:
                logger.debug("Using cached aurora data")
                return cached

        # Fetch fresh data
        data = self._fetch_from_api()
        if data:
            self._save_cache(data)
            return data

        # Fall back to stale cache if API fails
        if self.cache_file.exists():
            logger.warning("API failed, using stale cache")
            return self._load_cache()

        return None
