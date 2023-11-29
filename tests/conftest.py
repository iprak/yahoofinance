"""Tests for Yahoo Finance component."""
import json
import os
from unittest.mock import AsyncMock

import pytest

from custom_components.yahoofinance.const import DEFAULT_SCAN_INTERVAL
from custom_components.yahoofinance.coordinator import (
    CrumbCoordinator,
    YahooSymbolUpdateCoordinator,
)
from homeassistant.core import HomeAssistant
from tests import TEST_CRUMB, TEST_SYMBOL


def load_json(filename):
    """Load sample JSON."""
    path = os.path.join(os.path.dirname(__file__), filename)
    with open(path, encoding="utf-8") as fptr:
        return fptr.read()


def create_mock_coordinator(hass: HomeAssistant, crumb_coordinator: CrumbCoordinator) -> YahooSymbolUpdateCoordinator:
    """Create a test Coordinator."""

    coordinator = YahooSymbolUpdateCoordinator(
        [TEST_SYMBOL], hass, DEFAULT_SCAN_INTERVAL, crumb_coordinator
    )

    coordinator.last_update_success = False
    return coordinator


@pytest.fixture
def mock_json():
    """Return sample JSON data."""
    yield json.loads(load_json("yahoofinance.json"))


@pytest.fixture(name="mocked_crumb_coordinator")
def create_mock_crumb_coordinator(hass: HomeAssistant) -> CrumbCoordinator:
    """Fixture to provide a test instance of CrumbCoordinator."""
    crumb = TEST_CRUMB
    instance = CrumbCoordinator(hass)
    instance.try_get_crumb_cookies = AsyncMock(return_value=crumb)
    return instance
