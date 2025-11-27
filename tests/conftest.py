"""Tests for Yahoo Finance component."""

import json
import os
from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import pytest

from custom_components.yahoofinance.const import DEFAULT_SCAN_INTERVAL
from custom_components.yahoofinance.coordinator import (
    CrumbCoordinator,
    YahooSymbolUpdateCoordinator,
)

from . import TEST_CRUMB, TEST_SYMBOL

SESSION = async_get_clientsession


def load_json(filename):
    """Load sample JSON."""
    path = os.path.join(os.path.dirname(__file__), filename)
    with open(path, encoding="utf-8") as fptr:
        return fptr.read()


def create_mock_coordinator(
    hass: HomeAssistant, crumb_coordinator: CrumbCoordinator
) -> YahooSymbolUpdateCoordinator:
    """Create a test Coordinator."""

    coordinator = YahooSymbolUpdateCoordinator(
        [TEST_SYMBOL], hass, DEFAULT_SCAN_INTERVAL, crumb_coordinator, SESSION
    )

    coordinator.last_update_success = False
    return coordinator


@pytest.fixture
def mock_json():
    """Return sample JSON data."""
    return json.loads(load_json("yahoofinance.json"))


@pytest.fixture
def multiple_sample_data() -> tuple[list[str], dict]:
    """Return sample JSON data and symbols."""

    json_data = json.loads(load_json("yahoofinance.json"))
    symbols: list[str] = [
        item["symbol"] for item in json_data["quoteResponse"]["result"]
    ]
    return symbols, json_data


@pytest.fixture(name="mocked_crumb_coordinator")
def create_mock_crumb_coordinator(hass: HomeAssistant) -> CrumbCoordinator:
    """Fixture to provide a test instance of CrumbCoordinator."""
    crumb = TEST_CRUMB
    instance = CrumbCoordinator(hass, SESSION)
    instance.try_get_crumb_cookies = AsyncMock(return_value=crumb)
    return instance
