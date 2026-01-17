"""Base class for data providers."""

from abc import ABC, abstractmethod
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class BaseProvider(ABC):
    """
    Base class for overlay data providers.

    Each provider fetches data from an external source and formats it
    for use in raspilapse overlays.
    """

    # Provider name (override in subclass)
    name: str = "base"

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the provider.

        Args:
            config: Provider-specific configuration
        """
        self.config = config
        self.enabled = config.get("enabled", True)

    @abstractmethod
    def fetch(self) -> List[Dict[str, Any]]:
        """
        Fetch data from the external source.

        Returns:
            List of data items
        """
        pass

    @abstractmethod
    def format_for_overlay(self, items: List[Dict[str, Any]]) -> List[str]:
        """
        Format items as text lines for overlay display.

        Args:
            items: List of data items from fetch()

        Returns:
            List of formatted text strings
        """
        pass

    def get_overlay_text(self) -> str:
        """
        Get formatted overlay text.

        Returns:
            Multi-line string for overlay
        """
        if not self.enabled:
            return ""

        try:
            items = self.fetch()
            lines = self.format_for_overlay(items)
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Error in {self.name} provider: {e}")
            return f"{self.name}: error"

    def is_enabled(self) -> bool:
        """Check if provider is enabled."""
        return self.enabled
