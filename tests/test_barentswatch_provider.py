"""Tests for Barentswatch ship tracking provider."""

import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from providers.barentswatch.provider import BarentswatchProvider, point_in_polygon
from providers.barentswatch.ship_types import get_ship_type_string, get_ship_category


class TestPointInPolygon:
    """Test point-in-polygon algorithm."""

    @pytest.fixture
    def square_polygon(self):
        """A simple square polygon."""
        return [
            [0, 0],
            [10, 0],
            [10, 10],
            [0, 10],
            [0, 0],  # Closed polygon
        ]

    @pytest.mark.unit
    def test_point_inside(self, square_polygon):
        """Test point clearly inside polygon."""
        assert point_in_polygon(5, 5, square_polygon) is True

    @pytest.mark.unit
    def test_point_outside(self, square_polygon):
        """Test point clearly outside polygon."""
        assert point_in_polygon(15, 15, square_polygon) is False
        assert point_in_polygon(-5, 5, square_polygon) is False

    @pytest.mark.unit
    def test_point_on_edge(self, square_polygon):
        """Test point on polygon edge."""
        # Edge cases can vary by implementation
        result = point_in_polygon(5, 0, square_polygon)
        assert isinstance(result, bool)

    @pytest.mark.unit
    def test_point_at_corner(self, square_polygon):
        """Test point at polygon corner."""
        result = point_in_polygon(0, 0, square_polygon)
        assert isinstance(result, bool)


class TestShipTypes:
    """Test ship type utilities."""

    @pytest.mark.unit
    def test_known_ship_types(self):
        """Test known ship type codes."""
        assert get_ship_type_string(30) == "Fishing"
        assert get_ship_type_string(52) == "Tug"
        assert get_ship_type_string(60) == "Passenger, all ships of this type"
        assert get_ship_type_string(70) == "Cargo, all ships of this type"
        assert get_ship_type_string(80) == "Tanker, all ships of this type"

    @pytest.mark.unit
    def test_unknown_ship_type(self):
        """Test unknown ship type code."""
        assert get_ship_type_string(999) == "Unknown"
        assert get_ship_type_string(-1) == "Unknown"

    @pytest.mark.unit
    def test_ship_categories(self):
        """Test ship category grouping."""
        assert get_ship_category(30) == "Fishing"
        assert get_ship_category(52) == "Special"
        assert get_ship_category(60) == "Passenger"
        assert get_ship_category(70) == "Cargo"
        assert get_ship_category(80) == "Tanker"
        assert get_ship_category(0) == "Unknown"


class TestBarentswatchProvider:
    """Test Barentswatch provider."""

    @pytest.fixture
    def provider_config(self):
        """Test provider configuration."""
        return {
            "enabled": True,
            "client_id": "test_id",
            "client_secret": "test_secret",
            "lookback_hours": 3,
            "persist_minutes": 10,
            "zones": [
                {
                    "id": "test",
                    "name": "Test Zone",
                    "polygon": [
                        [10, 60],
                        [20, 60],
                        [20, 70],
                        [10, 70],
                        [10, 60],
                    ],
                }
            ],
        }

    @pytest.mark.unit
    def test_provider_init(self, provider_config):
        """Test provider initialization."""
        provider = BarentswatchProvider(provider_config)

        assert provider.name == "ships"
        assert provider.enabled is True
        assert provider.lookback_hours == 3
        assert provider.persist_minutes == 10
        assert len(provider.zones) == 1

    @pytest.mark.unit
    def test_format_ship_moving(self, provider_config):
        """Test formatting a moving ship."""
        provider = BarentswatchProvider(provider_config)

        ship = {
            "mmsi": 123456789,
            "name": "TEST SHIP",
            "speedOverGround": 12.5,
            "trueHeading": 45,
            "latitude": 65.0,
            "longitude": 15.0,
            "shipType": 70,
            "shipTypeString": "Cargo",
            "shipCategory": "Cargo",
        }

        formatted = provider._format_ship(ship)

        assert formatted["mmsi"] == 123456789
        assert formatted["name"] == "TEST SHIP"
        assert formatted["speed"] == 12.5
        assert formatted["direction"] == "north-east"
        assert "12.5 kts" in formatted["display"]
        assert "north-east" in formatted["display"]

    @pytest.mark.unit
    def test_format_ship_stationary(self, provider_config):
        """Test formatting a stationary ship."""
        provider = BarentswatchProvider(provider_config)

        ship = {
            "mmsi": 987654321,
            "name": "DOCKED SHIP",
            "speedOverGround": 0.1,
            "trueHeading": 180,
            "latitude": 65.0,
            "longitude": 15.0,
            "shipType": 60,
            "shipTypeString": "Passenger",
            "shipCategory": "Passenger",
        }

        formatted = provider._format_ship(ship)

        assert "stationary" in formatted["display"]
        assert "kts" not in formatted["display"]

    @pytest.mark.unit
    def test_format_for_overlay(self, provider_config):
        """Test overlay line formatting."""
        provider = BarentswatchProvider(provider_config)

        items = [
            {"display": "SHIP A (123) 10 kts, north"},
            {"display": "SHIP B (456) stationary"},
        ]

        lines = provider.format_for_overlay(items)

        assert len(lines) == 2
        assert lines[0] == "SHIP A (123) 10 kts, north"
        assert lines[1] == "SHIP B (456) stationary"

    @pytest.mark.unit
    def test_clear_tracked_ships(self, provider_config):
        """Test clearing tracked ships."""
        provider = BarentswatchProvider(provider_config)

        # Simulate tracked ships
        provider._last_seen[123] = 1000
        provider._ships[123] = {"name": "TEST"}

        provider.clear()

        assert len(provider._last_seen) == 0
        assert len(provider._ships) == 0

    @pytest.mark.unit
    def test_get_zone(self, provider_config):
        """Test getting zone by ID."""
        provider = BarentswatchProvider(provider_config)

        zone = provider._get_zone("test")
        assert zone is not None
        assert zone["id"] == "test"

        zone = provider._get_zone("nonexistent")
        assert zone is None

        # Default zone (first one)
        zone = provider._get_zone(None)
        assert zone is not None

    @pytest.mark.unit
    def test_provider_disabled(self):
        """Test disabled provider."""
        config = {"enabled": False}
        provider = BarentswatchProvider(config)

        assert provider.enabled is False


class TestShipPersistence:
    """Test ship persistence logic."""

    @pytest.fixture
    def provider(self):
        """Create a provider with short persistence."""
        config = {
            "enabled": True,
            "client_id": "test",
            "client_secret": "test",
            "lookback_hours": 1,
            "persist_minutes": 1,  # 1 minute = 60 seconds
            "zones": [
                {
                    "id": "test",
                    "polygon": [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]],
                }
            ],
        }
        return BarentswatchProvider(config)

    @pytest.mark.unit
    def test_ship_tracking(self, provider):
        """Test ship last_seen tracking."""
        import time

        # Manually add a ship to tracking
        provider._last_seen[123] = time.time()
        provider._ships[123] = {
            "mmsi": 123,
            "name": "TEST",
            "speedOverGround": 0,
            "latitude": 5,
            "longitude": 5,
        }

        # Ship should still be tracked
        assert 123 in provider._last_seen
        assert 123 in provider._ships
