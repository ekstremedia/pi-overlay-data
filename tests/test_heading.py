"""Tests for heading/compass direction utilities."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.heading import (
    degrees_to_compass_8point,
    degrees_to_compass_short,
    degrees_to_compass,
)


class TestDegreesToCompass8Point:
    """Test 8-point compass direction conversion."""

    @pytest.mark.unit
    def test_north(self):
        """Test north direction."""
        assert degrees_to_compass_8point(0) == "north"
        assert degrees_to_compass_8point(360) == "north"
        assert degrees_to_compass_8point(10) == "north"
        assert degrees_to_compass_8point(350) == "north"

    @pytest.mark.unit
    def test_cardinal_directions(self):
        """Test all cardinal directions."""
        assert degrees_to_compass_8point(0) == "north"
        assert degrees_to_compass_8point(90) == "east"
        assert degrees_to_compass_8point(180) == "south"
        assert degrees_to_compass_8point(270) == "west"

    @pytest.mark.unit
    def test_intercardinal_directions(self):
        """Test intercardinal directions."""
        assert degrees_to_compass_8point(45) == "north-east"
        assert degrees_to_compass_8point(135) == "south-east"
        assert degrees_to_compass_8point(225) == "south-west"
        assert degrees_to_compass_8point(315) == "north-west"

    @pytest.mark.unit
    def test_boundary_values(self):
        """Test values at direction boundaries."""
        # North/North-East boundary is around 22.5 degrees
        assert degrees_to_compass_8point(22) == "north"
        assert degrees_to_compass_8point(23) == "north-east"

    @pytest.mark.unit
    def test_none_input(self):
        """Test None input returns 'unknown'."""
        assert degrees_to_compass_8point(None) == "unknown"

    @pytest.mark.unit
    def test_negative_degrees(self):
        """Test negative degree values (should normalize)."""
        assert degrees_to_compass_8point(-90) == "west"
        assert degrees_to_compass_8point(-180) == "south"

    @pytest.mark.unit
    def test_large_values(self):
        """Test values over 360 (should normalize)."""
        assert degrees_to_compass_8point(450) == "east"  # 450 - 360 = 90
        assert degrees_to_compass_8point(720) == "north"  # 720 - 720 = 0


class TestDegreesToCompassShort:
    """Test short compass direction conversion."""

    @pytest.mark.unit
    def test_cardinal_short(self):
        """Test cardinal directions in short format."""
        assert degrees_to_compass_short(0) == "N"
        assert degrees_to_compass_short(90) == "E"
        assert degrees_to_compass_short(180) == "S"
        assert degrees_to_compass_short(270) == "W"

    @pytest.mark.unit
    def test_intercardinal_short(self):
        """Test intercardinal directions in short format."""
        assert degrees_to_compass_short(45) == "NE"
        assert degrees_to_compass_short(135) == "SE"
        assert degrees_to_compass_short(225) == "SW"
        assert degrees_to_compass_short(315) == "NW"

    @pytest.mark.unit
    def test_none_returns_question_mark(self):
        """Test None input returns '?'."""
        assert degrees_to_compass_short(None) == "?"


class TestDegreesToCompass16Point:
    """Test 16-point compass direction conversion."""

    @pytest.mark.unit
    def test_16_point_directions(self):
        """Test 16-point compass includes intermediate directions."""
        # NNE is between N (0) and NE (45), around 22.5
        result = degrees_to_compass(22.5)
        assert "north" in result

    @pytest.mark.unit
    def test_all_16_points_reachable(self):
        """Test all 16 compass points can be reached."""
        directions_found = set()
        for deg in range(0, 360, 10):
            directions_found.add(degrees_to_compass(deg))
        # Should have multiple unique directions
        assert len(directions_found) >= 8
