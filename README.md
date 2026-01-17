# Pi-Overlay-Data

A modular service that collects overlay data from multiple sources for use in raspilapse timelapses.

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

# 3. Test
./venv/bin/python run.py --zone testing

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

### Zones (config/config.json)

Define polygon areas to monitor. Use https://geojson.io to draw polygons.

```json
{
  "zones": [
    {
      "id": "my_camera",
      "name": "Camera Location",
      "polygon": [[lon, lat], [lon, lat], ...]
    }
  ]
}
```

## Usage

```bash
./venv/bin/python run.py              # Run once
./venv/bin/python run.py --loop       # Run continuously (60s interval)
./venv/bin/python run.py --zone testing --verbose
./venv/bin/python run.py --list-zones
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
├── config/
│   └── config.json        # Zone configurations
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

### Linting

```bash
ruff check .
```

## Service Management

```bash
sudo systemctl status pi-overlay-data
sudo systemctl restart pi-overlay-data
journalctl -u pi-overlay-data -f
```
