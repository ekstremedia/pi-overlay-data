# Pi-Overlay-Data

A modular service that collects overlay data from multiple sources for use in raspilapse timelapses.

**Requires Python 3.9+**

## Data Providers

| Provider | Status | Description |
|----------|--------|-------------|
| **Ships** | Working | Barentswatch AIS ship tracking |
| **Aurora** | Planned | Northern lights forecast |
| **Tides** | Planned | Water level/tide data |

## Quick Start

```bash
cd /www/pi-overlay-data

# 1. Create virtual environment
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# 2. Configure
cp .env.example .env
nano .env  # Add your credentials

cp geojson/zone.example.json geojson/zone.json
nano geojson/zone.json  # Set your zone polygon

# 3. Test
./venv/bin/python run.py

# 4. Run as service
sudo cp pi-overlay-data.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pi-overlay-data
sudo systemctl start pi-overlay-data
```

## Configuration

### Environment (.env)

```bash
# Barentswatch ship tracking
BARENTSWATCH_ENABLED=true
BARENTSWATCH_CLIENT_ID=your_email:app_name
BARENTSWATCH_CLIENT_SECRET=your_secret
LOOKBACK_HOURS=3      # How far back to search
PERSIST_MINUTES=10    # How long ships stay visible after leaving

# Future providers
AURORA_ENABLED=false
TIDES_ENABLED=false
```

### Zone (geojson/zone.json)

Define the polygon area to monitor using standard GeoJSON.

**Creating your zone polygon:**
1. Open [geojson.io](https://geojson.io/#map=10.72/68.6288/15.3679) (link centered on northern Norway)
2. Use the polygon tool to draw your monitoring area
3. Copy the generated JSON and save it to `geojson/zone.json`

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {},
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [lon, lat],
          [lon, lat],
          [lon, lat],
          [lon, lat]
        ]]
      }
    }
  ]
}
```

Both `Polygon` and `LineString` geometry types are supported. LineStrings are automatically closed.

## Usage

```bash
./venv/bin/python run.py              # Run once
./venv/bin/python run.py --loop       # Run continuously (60s interval)
./venv/bin/python run.py --verbose
```

## Output Files

Data is written to `data/`:

```
data/
├── ships_current.json     # Ship data for raspilapse
├── ships_overlay.txt      # Text lines for overlay
└── combined_overlay.txt   # All providers combined
```

### ships_current.json

```json
{
  "provider": "ships",
  "updated_at": "2026-01-17T14:00:00+00:00",
  "count": 5,
  "items": [
    {
      "mmsi": 259139000,
      "name": "NORDLYS",
      "speed": 12.5,
      "heading": 344,
      "direction": "north-west",
      "display": "NORDLYS (259139000) 12.5 kts, north-west",
      "still_in_zone": true
    }
  ]
}
```

### ships_overlay.txt

```
NORDLYS (259139000) 12.5 kts, north-west
HAVDONN (258201000) stationary
MALANGEN (258149000) 8.3 kts, south
```

## Integration with Raspilapse

Read the overlay text file directly:

```python
def get_ship_overlay():
    try:
        with open("/www/pi-overlay-data/data/ships_overlay.txt") as f:
            return f.read()
    except:
        return ""
```

Or parse the JSON for more control:

```python
import json

def get_ships():
    with open("/www/pi-overlay-data/data/ships_current.json") as f:
        data = json.load(f)
    return data["items"]
```

## Ship Persistence

Ships remain visible for `PERSIST_MINUTES` after leaving the zone.
This prevents rapid blinking in the timelapse when ships briefly leave and re-enter.

At 2 photos/minute and 25fps playback:
- 10 minutes = ~20 frames = ~0.8 seconds of video
- Adjust PERSIST_MINUTES based on your timelapse speed

## Project Structure

```
/www/pi-overlay-data/
├── run.py                 # Main entry point
├── config.py              # Configuration
├── .env                   # Credentials (don't commit)
├── core/                  # Shared utilities
│   ├── base_provider.py   # Provider base class
│   ├── heading.py         # Compass direction utils
│   └── overlay_output.py  # Output file handling
├── providers/
│   ├── barentswatch/      # Ship tracking
│   ├── aurora/            # Northern lights (TODO)
│   └── tides/             # Water levels (TODO)
├── geojson/
│   ├── zone.json          # Zone polygon (don't commit)
│   └── zone.example.json  # Example zone config
├── tests/                 # Unit tests
└── data/                  # Output files
```

## Development

### Install dev dependencies

```bash
./venv/bin/pip install -r requirements-dev.txt
```

### Run tests

```bash
# Run all tests
./venv/bin/pytest

# Run unit tests only (no network required)
./venv/bin/pytest -m unit

# Run with coverage
./venv/bin/pytest --cov=core --cov=providers --cov-report=term-missing
```

### Linting & Formatting

```bash
# Format code
black .

# Check linting
ruff check .

# Fix auto-fixable lint errors
ruff check . --fix
```

### Pre-commit hooks

Install pre-commit hooks to auto-format on commit:

```bash
./venv/bin/pip install pre-commit
pre-commit install
```

This will run black and ruff automatically before each commit.

## Service Management

```bash
sudo systemctl status pi-overlay-data
sudo systemctl restart pi-overlay-data
journalctl -u pi-overlay-data -f
```
