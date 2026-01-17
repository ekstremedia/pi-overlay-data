"""Barentswatch AIS API client."""

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any

import requests

from .ship_types import get_ship_type_string, get_ship_category

logger = logging.getLogger(__name__)


class BarentswatchClient:
    """Client for the Barentswatch AIS API."""

    TOKEN_URL = "https://id.barentswatch.no/connect/token"
    HISTORIC_API_URL = "https://historic.ais.barentswatch.no/v1/historic/mmsiinarea"
    LIVE_API_URL = "https://live.ais.barentswatch.no/v1/latest/combined"

    def __init__(self, client_id: str, client_secret: str):
        """
        Initialize the Barentswatch client.

        Args:
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
        self._session = requests.Session()

    def _get_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary.

        Returns:
            Valid access token
        """
        # Check if we have a valid token
        if self._access_token and time.time() < self._token_expires_at - 60:
            return self._access_token

        logger.debug("Requesting new access token")

        response = self._session.post(
            self.TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
                "scope": "ais",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        response.raise_for_status()
        token_data = response.json()

        self._access_token = token_data["access_token"]
        # Set expiry time (tokens usually last 1 hour)
        expires_in = token_data.get("expires_in", 3600)
        self._token_expires_at = time.time() + expires_in

        logger.debug(f"Got new token, expires in {expires_in}s")
        return self._access_token

    def _make_authenticated_request(
        self,
        method: str,
        url: str,
        json_data: Optional[Dict] = None,
    ) -> Any:
        """
        Make an authenticated request to the API.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: API endpoint URL
            json_data: JSON payload for POST requests

        Returns:
            Parsed JSON response
        """
        token = self._get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = self._session.request(
            method,
            url,
            json=json_data,
            headers=headers,
        )

        response.raise_for_status()
        return response.json()

    def get_ships_in_polygon(
        self,
        polygon: List[List[float]],
        lookback_hours: int = 3,
    ) -> List[int]:
        """
        Get MMSI numbers of ships that have been in a polygon area.

        Args:
            polygon: List of [longitude, latitude] coordinates defining the polygon
            lookback_hours: How far back to search for ships

        Returns:
            List of MMSI numbers
        """
        now = datetime.now(timezone.utc)
        from_time = now - timedelta(hours=lookback_hours)

        payload = {
            "msgtimefrom": from_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "msgtimeto": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "polygon": {
                "type": "Polygon",
                "coordinates": [polygon],
            },
        }

        logger.debug(f"Querying ships in polygon from {from_time} to {now}")

        mmsi_list = self._make_authenticated_request(
            "POST",
            self.HISTORIC_API_URL,
            json_data=payload,
        )

        logger.debug(f"Found {len(mmsi_list)} ships in polygon")
        return mmsi_list

    def get_vessel_details(self, mmsi_list: List[int]) -> List[Dict[str, Any]]:
        """
        Get detailed information for a list of vessels.

        Args:
            mmsi_list: List of MMSI numbers

        Returns:
            List of vessel detail dictionaries
        """
        if not mmsi_list:
            return []

        payload = {"mmsi": mmsi_list}

        logger.debug(f"Getting details for {len(mmsi_list)} vessels")

        vessels = self._make_authenticated_request(
            "POST",
            self.LIVE_API_URL,
            json_data=payload,
        )

        # Enrich with ship type strings
        for vessel in vessels:
            ship_type = vessel.get("shipType", 0)
            vessel["shipTypeString"] = get_ship_type_string(ship_type)
            vessel["shipCategory"] = get_ship_category(ship_type)

        logger.debug(f"Got details for {len(vessels)} vessels")
        return vessels

    def get_ships_in_area(
        self,
        polygon: List[List[float]],
        lookback_hours: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Get full details of ships in a polygon area.

        This combines get_ships_in_polygon and get_vessel_details.

        Args:
            polygon: List of [longitude, latitude] coordinates defining the polygon
            lookback_hours: How far back to search for ships

        Returns:
            List of vessel detail dictionaries
        """
        mmsi_list = self.get_ships_in_polygon(polygon, lookback_hours)
        return self.get_vessel_details(mmsi_list)
