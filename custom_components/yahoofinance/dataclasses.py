"""Data classes for Yahoo finance component."""

from dataclasses import dataclass
from datetime import time, timedelta

from homeassistant.const import CONF_SCAN_INTERVAL

from .const import (
    CONF_ACTIVE_DAYS,
    CONF_ACTIVE_END,
    CONF_ACTIVE_START,
    CONF_NO_UNIT,
    CONF_TARGET_CURRENCY,
)


class SymbolDefinition:
    """Symbol definition."""

    symbol: str
    target_currency: str | None = None
    scan_interval: str | timedelta | None = None
    no_unit: bool = False
    active_start: time | None = None
    active_end: time | None = None
    active_days: list[int] | None = None

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
        if CONF_ACTIVE_START in kwargs:
            self.active_start = kwargs[CONF_ACTIVE_START]
        if CONF_ACTIVE_END in kwargs:
            self.active_end = kwargs[CONF_ACTIVE_END]
        if CONF_ACTIVE_DAYS in kwargs:
            self.active_days = kwargs[CONF_ACTIVE_DAYS]

    @property
    def coordinator_key(self) -> tuple:
        """Return key used for grouping symbols into coordinators."""
        active_days_tuple = tuple(self.active_days) if self.active_days is not None else None
        return (
            self.scan_interval,
            self.active_start,
            self.active_end,
            active_days_tuple,
        )

    def __repr__(self) -> str:
        """Return the representation."""
        return (
            f"{self.symbol},{self.target_currency},{self.scan_interval},{self.no_unit},"
            f"{self.active_start},{self.active_end},{self.active_days}"
        )

    def __eq__(self, other: any) -> bool:
        """Return the comparison."""
        return (
            isinstance(other, SymbolDefinition)
            and self.symbol == other.symbol
            and self.target_currency == other.target_currency
            and self.scan_interval == other.scan_interval
            and self.no_unit == other.no_unit
            and self.active_start == other.active_start
            and self.active_end == other.active_end
            and self.active_days == other.active_days
        )

    def __hash__(self) -> int:
        """Make hashable."""
        active_days_tuple = tuple(self.active_days) if self.active_days is not None else None
        return hash(
            (
                self.symbol,
                self.target_currency,
                self.scan_interval,
                self.no_unit,
                self.active_start,
                self.active_end,
                active_days_tuple,
            )
        )


@dataclass
class ConsentData:
    """Class for data related to GDPR consent."""

    consent_content: str = ""
    """Consent verification content"""
    consent_post_url: str = ""
    """Url from consent check where data is to be submitted"""
    successful_consent_url: str = ""
    """Url to navigate to after successful consent"""
    need_consent: bool = False
    """Consent is needed"""
