"""
Flask web server for the overlay data dashboard.

Serves API endpoints and the interactive Chart.js dashboard.

Usage:
    python web/server.py              # Run on port 5000
    python web/server.py --port 8080  # Custom port
"""

import argparse
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, jsonify, render_template, request

# Setup paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

app = Flask(__name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static")
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_json_file(filename: str) -> dict:
    """Load a JSON file from the data directory."""
    filepath = DATA_DIR / filename
    if filepath.exists():
        with open(filepath) as f:
            return json.load(f)
    return {}


def parse_iso_datetime(dt_str: str) -> datetime:
    """Parse ISO datetime string."""
    # Handle various ISO formats
    dt_str = dt_str.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(dt_str)
    except ValueError:
        # Fallback for edge cases
        return datetime.now()


# ============== API ENDPOINTS ==============

@app.route("/api/tides")
def api_tides():
    """
    Get tide data.

    Query params:
        hours: Number of hours to return (default: 24)
    """
    hours = request.args.get("hours", 24, type=int)
    hours = min(max(hours, 1), 48)  # Clamp between 1 and 48

    data = load_json_file("tide.json")
    if not data:
        return jsonify({"error": "No tide data available"}), 404

    tide_data = data.get("tide_data", {})
    points = tide_data.get("points", [])

    # Filter points by time range if needed
    now = datetime.now().astimezone()
    cutoff = now - timedelta(hours=hours)

    filtered_points = []
    for point in points:
        try:
            point_time = parse_iso_datetime(point["time"])
            # Include points within range or future points
            filtered_points.append({
                "time": point["time"],
                "level_cm": point["level_cm"],
                "timestamp": point_time.isoformat()
            })
        except (KeyError, ValueError):
            continue

    return jsonify({
        "location": tide_data.get("location", "Unknown"),
        "fetched_at": data.get("fetched_at"),
        "points": filtered_points,
        "count": len(filtered_points)
    })


@app.route("/api/aurora")
def api_aurora():
    """Get current aurora data."""
    data = load_json_file("aurora_current.json")
    if not data or not data.get("items"):
        return jsonify({"error": "No aurora data available"}), 404

    item = data["items"][0]
    return jsonify({
        "kp": item.get("kp", 0),
        "bz": item.get("bz", 0),
        "bz_status": item.get("bz_status", "unknown"),
        "speed": item.get("speed", 0),
        "storm": item.get("storm", "G0"),
        "conditions": item.get("conditions", ""),
        "favorable": item.get("favorable", False),
        "updated_at": data.get("updated_at"),
        "generated_at": item.get("generated_at")
    })


@app.route("/api/ships")
def api_ships():
    """Get current ship data."""
    data = load_json_file("ships_current.json")
    if not data:
        return jsonify({"error": "No ship data available"}), 404

    return jsonify({
        "ships": data.get("items", []),
        "count": data.get("count", 0),
        "updated_at": data.get("updated_at")
    })


@app.route("/api/summary")
def api_summary():
    """Get a summary of all data sources."""
    tide_data = load_json_file("tide.json")
    aurora_data = load_json_file("aurora_current.json")
    ships_data = load_json_file("ships_current.json")

    summary = {
        "tides": {
            "available": bool(tide_data),
            "location": tide_data.get("tide_data", {}).get("location", "Unknown") if tide_data else None,
            "points_count": len(tide_data.get("tide_data", {}).get("points", [])) if tide_data else 0
        },
        "aurora": {
            "available": bool(aurora_data and aurora_data.get("items")),
            "kp": aurora_data["items"][0].get("kp") if aurora_data and aurora_data.get("items") else None,
            "favorable": aurora_data["items"][0].get("favorable") if aurora_data and aurora_data.get("items") else None
        },
        "ships": {
            "available": bool(ships_data),
            "count": ships_data.get("count", 0) if ships_data else 0
        }
    }

    return jsonify(summary)


# ============== DASHBOARD ==============

@app.route("/")
def dashboard():
    """Render the main dashboard."""
    return render_template("dashboard.html")


# ============== MAIN ==============

def main():
    parser = argparse.ArgumentParser(description="Overlay data dashboard server")
    parser.add_argument("--port", type=int, default=5000, help="Port to run on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    logger.info(f"Starting dashboard server on http://{args.host}:{args.port}")
    logger.info(f"Data directory: {DATA_DIR}")

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
