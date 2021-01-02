"""Tests for Yahoo Finance component."""

from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.async_mock import patch

from custom_components.yahoofinance import DEFAULT_SCAN_INTERVAL
from custom_components.yahoofinance.const import (
    CONF_DECIMAL_PLACES,
    CONF_SHOW_TRENDING_ICON,
    CONF_SYMBOLS,
    DEFAULT_CONF_SHOW_TRENDING_ICON,
    DEFAULT_DECIMAL_PLACES,
    DOMAIN,
    HASS_DATA_CONFIG,
    HASS_DATA_COORDINATOR,
)


@pytest.mark.parametrize(
    "test_config,expected",
    [
        (
            {DOMAIN: {CONF_SYMBOLS: ["xyz"]}},
            {
                CONF_SYMBOLS: ["XYZ"],
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                CONF_DECIMAL_PLACES: DEFAULT_DECIMAL_PLACES,
                CONF_SHOW_TRENDING_ICON: DEFAULT_CONF_SHOW_TRENDING_ICON,
            },
        ),
        (
            {DOMAIN: {CONF_SYMBOLS: ["xyz"], CONF_DECIMAL_PLACES: 3}},
            {
                CONF_SYMBOLS: ["XYZ"],
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                CONF_DECIMAL_PLACES: 3,
                CONF_SHOW_TRENDING_ICON: DEFAULT_CONF_SHOW_TRENDING_ICON,
            },
        ),
    ],
)
async def test_setup(hass, test_config, expected):
    """Set up sensor."""
    #       return_value=json.loads(load_fixture("yahoofinance.json")),

    with patch(
        "custom_components.yahoofinance.YahooSymbolUpdateCoordinator.update"
    ), patch(
        "custom_components.yahoofinance.YahooSymbolUpdateCoordinator.async_refresh"
    ):
        assert await async_setup_component(hass, DOMAIN, test_config) == True

    await hass.async_block_till_done()
    assert expected == hass.data[DOMAIN][HASS_DATA_CONFIG]

    # Verify that update_interval is passed correctly to DataCoordinator
    assert (
        expected[CONF_SCAN_INTERVAL]
        == hass.data[DOMAIN][HASS_DATA_COORDINATOR].update_interval
    )
