#!/usr/bin/env python3
"""
Pi-Overlay-Data

A modular service that collects overlay data from multiple sources
(ships, aurora, tides) for use in raspilapse timelapses.

Usage:
    python run.py              # Run once
    python run.py --loop       # Run continuously
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from core.overlay_output import OverlayOutput
from providers.barentswatch.provider import BarentswatchProvider


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


class OverlayDataService:
    """Main service that coordinates all data providers."""

    def __init__(self, config: Config):
        self.config = config
        self.data_dir = Path(config.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.output = OverlayOutput(self.data_dir)
        self.providers = {}

        # Initialize enabled providers
        if config.is_provider_enabled("barentswatch"):
            self.providers["ships"] = BarentswatchProvider(config.barentswatch)
            logging.info("Barentswatch ship provider enabled")

        # TODO: Add aurora and tides providers when implemented

    def run_once(self) -> None:
        """Fetch data from all providers and write output."""
        all_overlay_lines = {}

        for name, provider in self.providers.items():
            if name == "ships":
                items = provider.update()
                lines = provider.format_for_overlay(items)

                # Write provider-specific output
                self.output.write_provider_data(name, items, lines)
                all_overlay_lines[name] = lines

                logging.info(f"Ships: {len(items)} in zone")
            else:
                # Other providers
                items = provider.fetch()
                lines = provider.format_for_overlay(items)
                self.output.write_provider_data(name, items, lines)
                all_overlay_lines[name] = lines

        # Write combined overlay
        self.output.write_combined_overlay(all_overlay_lines)

    def run_loop(self, interval: int = 60) -> None:
        """Run continuously."""
        logging.info(f"Starting overlay data loop (interval: {interval}s)")

        while True:
            try:
                self.run_once()
            except KeyboardInterrupt:
                logging.info("Stopping")
                break
            except Exception as e:
                logging.error(f"Error: {e}")

            time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="Overlay data service for raspilapse")

    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument(
        "--interval", type=int, default=60, help="Update interval (seconds)"
    )
    parser.add_argument("--env", type=str, default=None, help="Path to .env file")
    parser.add_argument(
        "--config", type=str, default=None, help="Path to zone.json geojson file"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()
    setup_logging(args.verbose)

    # Load configuration
    config = Config(env_path=args.env, config_path=args.config)
    config.load_config()

    # Check barentswatch credentials
    if config.is_provider_enabled("barentswatch"):
        if not config.barentswatch.get("client_id"):
            print("Error: BARENTSWATCH_CLIENT_ID not set")
            sys.exit(1)

    if not config.polygon:
        print("Error: No zone configured. Create geojson/zone.json")
        sys.exit(1)

    # Create and run service
    service = OverlayDataService(config)

    if args.loop:
        service.run_loop(interval=args.interval)
    else:
        service.run_once()
        print(f"Data written to {config.data_dir}/")


if __name__ == "__main__":
    main()
