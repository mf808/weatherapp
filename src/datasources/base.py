from abc import ABC, abstractmethod


class DataSource(ABC):
    """Abstract base for all data sources."""

    @abstractmethod
    def fetch(self) -> dict:
        """Fetch data and return as a dict keyed by sensor/data name."""
        ...
