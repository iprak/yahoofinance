"""Data used by this integration."""

from dataclasses import dataclass
from datetime import timedelta

from homeassistant.const import CONF_SCAN_INTERVAL

from .const import CONF_NO_UNIT, CONF_TARGET_CURRENCY
from .coordinator import YahooSymbolUpdateCoordinator


@dataclass(frozen=True)
class YahooFinanceData:
    """Yahoo Finance data class."""

    coordinators: dict[int, YahooSymbolUpdateCoordinator]
    # symbols: list[SymbolDefinition]


@dataclass(frozen=True)
class SymbolData:
    """Symbol definition data class."""

    symbol: str
    target_currency: str
    scan_interval: int
    no_unit: bool


class SymbolDefinition:
    """Symbol definition."""

    symbol: str
    target_currency: str | None = None
    scan_interval: str | timedelta | None = None
    no_unit: bool = False

    def __init__(self, symbol: str, **kwargs: any) -> None:
        """Create a new symbol definition.

        ### Parameters
            symbol(str): The symbol
            **scan_interval (time_delta): The symbol scan interval
        """
        self.symbol = symbol

        if CONF_TARGET_CURRENCY in kwargs:
            self.target_currency = kwargs[CONF_TARGET_CURRENCY]
        if CONF_SCAN_INTERVAL in kwargs:
            self.scan_interval = kwargs[CONF_SCAN_INTERVAL]
        if CONF_NO_UNIT in kwargs:
            self.no_unit = kwargs[CONF_NO_UNIT]

    def __repr__(self) -> str:
        """Return the representation."""
        return (
            f"{self.symbol},{self.target_currency},{self.scan_interval},{self.no_unit}"
        )

    def __eq__(self, other: any) -> bool:
        """Return the comparison."""
        return (
            isinstance(other, SymbolDefinition)
            and self.symbol == other.symbol
            and self.target_currency == other.target_currency
            and self.scan_interval == other.scan_interval
            and self.no_unit == other.no_unit
        )

    def __hash__(self) -> int:
        """Make hashable."""
        return hash(
            (self.symbol, self.target_currency, self.scan_interval, self.no_unit)
        )
