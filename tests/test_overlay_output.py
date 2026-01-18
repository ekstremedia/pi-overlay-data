"""Tests for overlay output module."""

import pytest
import os
import sys
import json
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.overlay_output import OverlayOutput


class TestOverlayOutput:
    """Test OverlayOutput class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.mark.unit
    def test_init_creates_directory(self, temp_dir):
        """Test that init creates the data directory if it doesn't exist."""
        new_dir = os.path.join(temp_dir, "subdir", "data")
        output = OverlayOutput(new_dir)

        assert os.path.exists(new_dir)
        assert output.data_dir == Path(new_dir)

    @pytest.mark.unit
    def test_init_with_existing_directory(self, temp_dir):
        """Test init with existing directory."""
        output = OverlayOutput(temp_dir)

        assert output.data_dir == Path(temp_dir)
        assert output.stale_seconds == 5 * 60  # default 5 minutes

    @pytest.mark.unit
    def test_init_custom_stale_minutes(self, temp_dir):
        """Test init with custom stale_minutes."""
        output = OverlayOutput(temp_dir, stale_minutes=10)

        assert output.stale_seconds == 10 * 60

    @pytest.mark.unit
    def test_write_provider_data_json(self, temp_dir):
        """Test writing provider data to JSON file."""
        output = OverlayOutput(temp_dir)

        items = [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
        ]
        overlay_lines = ["Line 1", "Line 2"]

        output.write_provider_data("test", items, overlay_lines)

        # Check JSON file
        json_file = os.path.join(temp_dir, "test_current.json")
        assert os.path.exists(json_file)

        with open(json_file) as f:
            data = json.load(f)

        assert data["provider"] == "test"
        assert data["count"] == 2
        assert len(data["items"]) == 2
        assert "updated_at" in data

    @pytest.mark.unit
    def test_write_provider_data_text(self, temp_dir):
        """Test writing provider data to text overlay file."""
        output = OverlayOutput(temp_dir)

        items = [{"id": 1}]
        overlay_lines = ["Ship A heading north", "Ship B stationary"]

        output.write_provider_data("ships", items, overlay_lines)

        # Check text file
        text_file = os.path.join(temp_dir, "ships_overlay.txt")
        assert os.path.exists(text_file)

        with open(text_file) as f:
            content = f.read()

        assert "Ship A heading north" in content
        assert "Ship B stationary" in content

    @pytest.mark.unit
    def test_write_provider_data_empty_lines(self, temp_dir):
        """Test writing provider data with empty overlay lines."""
        output = OverlayOutput(temp_dir)

        output.write_provider_data("empty", [], [])

        text_file = os.path.join(temp_dir, "empty_overlay.txt")
        with open(text_file) as f:
            content = f.read()

        assert content == ""

    @pytest.mark.unit
    def test_write_combined_overlay(self, temp_dir):
        """Test writing combined overlay from multiple providers."""
        output = OverlayOutput(temp_dir)

        provider_data = {
            "ships": ["Ship A", "Ship B"],
            "aurora": ["Aurora: Kp 5"],
            "tides": [],  # Empty should be skipped
        }

        output.write_combined_overlay(provider_data)

        combined_file = os.path.join(temp_dir, "combined_overlay.txt")
        assert os.path.exists(combined_file)

        with open(combined_file) as f:
            content = f.read()

        assert "Ship A" in content
        assert "Ship B" in content
        assert "Aurora: Kp 5" in content

    @pytest.mark.unit
    def test_write_combined_overlay_all_empty(self, temp_dir):
        """Test combined overlay when all providers are empty."""
        output = OverlayOutput(temp_dir)

        provider_data = {
            "ships": [],
            "aurora": [],
        }

        output.write_combined_overlay(provider_data)

        combined_file = os.path.join(temp_dir, "combined_overlay.txt")
        with open(combined_file) as f:
            content = f.read()

        assert content == "No data"

    @pytest.mark.unit
    def test_startup_cleanup_stale_data(self, temp_dir):
        """Test that startup clears stale data files."""
        # Create a stale data file
        stale_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        stale_data = {
            "updated_at": stale_time.isoformat(),
            "count": 5,
            "items": [{"id": 1}],
        }

        stale_file = os.path.join(temp_dir, "ships_current.json")
        with open(stale_file, "w") as f:
            json.dump(stale_data, f)

        # Create OverlayOutput which should clean up stale data
        OverlayOutput(temp_dir, stale_minutes=5)

        # Check that the file was cleared
        with open(stale_file) as f:
            data = json.load(f)

        assert data["count"] == 0
        assert data["items"] == []

    @pytest.mark.unit
    def test_startup_keeps_fresh_data(self, temp_dir):
        """Test that startup keeps fresh (non-stale) data files."""
        # Create a fresh data file
        fresh_time = datetime.now(timezone.utc) - timedelta(minutes=1)
        fresh_data = {
            "updated_at": fresh_time.isoformat(),
            "count": 3,
            "items": [{"id": 1}, {"id": 2}, {"id": 3}],
        }

        fresh_file = os.path.join(temp_dir, "ships_current.json")
        with open(fresh_file, "w") as f:
            json.dump(fresh_data, f)

        # Create OverlayOutput which should keep fresh data
        OverlayOutput(temp_dir, stale_minutes=5)

        # Check that the file was kept
        with open(fresh_file) as f:
            data = json.load(f)

        assert data["count"] == 3
        assert len(data["items"]) == 3


class TestOverlayOutputEdgeCases:
    """Test edge cases for OverlayOutput."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.mark.unit
    def test_handles_corrupt_json(self, temp_dir):
        """Test that startup handles corrupt JSON files gracefully."""
        corrupt_file = os.path.join(temp_dir, "corrupt_current.json")
        with open(corrupt_file, "w") as f:
            f.write("not valid json {{{")

        # Should not raise exception
        output = OverlayOutput(temp_dir)
        assert output is not None

    @pytest.mark.unit
    def test_handles_missing_updated_at(self, temp_dir):
        """Test that startup handles files without updated_at field."""
        data_file = os.path.join(temp_dir, "notime_current.json")
        with open(data_file, "w") as f:
            json.dump({"count": 1, "items": []}, f)

        # Should not raise exception
        output = OverlayOutput(temp_dir)
        assert output is not None

    @pytest.mark.unit
    def test_path_as_string(self, temp_dir):
        """Test that path works as string."""
        output = OverlayOutput(str(temp_dir))
        assert output.data_dir == Path(temp_dir)

    @pytest.mark.unit
    def test_path_as_path_object(self, temp_dir):
        """Test that path works as Path object."""
        output = OverlayOutput(Path(temp_dir))
        assert output.data_dir == Path(temp_dir)
