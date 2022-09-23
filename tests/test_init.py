"""Tests for Yahoo Finance component."""

from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.setup import async_setup_component
import pytest
import voluptuous as vol

from custom_components.yahoofinance import (
    SymbolDefinition,
    convert_to_float,
    parse_scan_interval,
)
from custom_components.yahoofinance.const import (
    CONF_DECIMAL_PLACES,
    CONF_INCLUDE_FIFTY_DAY_VALUES,
    CONF_INCLUDE_POST_VALUES,
    CONF_INCLUDE_PRE_VALUES,
    CONF_INCLUDE_TWO_HUNDRED_DAY_VALUES,
    CONF_SHOW_TRENDING_ICON,
    CONF_SYMBOLS,
    DEFAULT_CONF_DECIMAL_PLACES,
    DEFAULT_CONF_INCLUDE_FIFTY_DAY_VALUES,
    DEFAULT_CONF_INCLUDE_POST_VALUES,
    DEFAULT_CONF_INCLUDE_PRE_VALUES,
    DEFAULT_CONF_INCLUDE_TWO_HUNDRED_DAY_VALUES,
    DEFAULT_CONF_SHOW_TRENDING_ICON,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    HASS_DATA_CONFIG,
    MINIMUM_SCAN_INTERVAL,
    SERVICE_REFRESH,
)

SAMPLE_CONFIG = {DOMAIN: {CONF_SYMBOLS: ["BABA"]}}
YSUC = "custom_components.yahoofinance.YahooSymbolUpdateCoordinator"
DEFAULT_OPTIONAL_CONFIG = {
    CONF_DECIMAL_PLACES: DEFAULT_CONF_DECIMAL_PLACES,
    CONF_INCLUDE_FIFTY_DAY_VALUES: DEFAULT_CONF_INCLUDE_FIFTY_DAY_VALUES,
    CONF_INCLUDE_POST_VALUES: DEFAULT_CONF_INCLUDE_POST_VALUES,
    CONF_INCLUDE_PRE_VALUES: DEFAULT_CONF_INCLUDE_PRE_VALUES,
    CONF_INCLUDE_TWO_HUNDRED_DAY_VALUES: DEFAULT_CONF_INCLUDE_TWO_HUNDRED_DAY_VALUES,
    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
    CONF_SHOW_TRENDING_ICON: DEFAULT_CONF_SHOW_TRENDING_ICON,
}


def create_symbol_definition(symbol: str) -> SymbolDefinition:
    """Create a SymbolDefinition with DEFAULT_SCAN_INTERVAL."""
    return SymbolDefinition(symbol, scan_interval=DEFAULT_SCAN_INTERVAL)


@pytest.mark.parametrize(
    "domain_config, expected_partial_config",
    [
        (
            # Normalize test
            {CONF_SYMBOLS: ["xyz"]},
            {CONF_SYMBOLS: [create_symbol_definition("XYZ")]},
        ),
        (
            # Another normalize test
            {CONF_SYMBOLS: [{"symbol": "xyz"}]},
            {CONF_SYMBOLS: [create_symbol_definition("XYZ")]},
        ),
        (
            {CONF_SYMBOLS: [{"symbol": "xyz"}, "abc"]},
            {
                CONF_SYMBOLS: [
                    create_symbol_definition("XYZ"),
                    create_symbol_definition("ABC"),
                ]
            },
        ),
        (
            # Duplicate removal test
            {CONF_SYMBOLS: ["xyz", "xyz"]},
            {CONF_SYMBOLS: [create_symbol_definition("XYZ")]},
        ),
        (
            # Another duplicate removal test
            {CONF_SYMBOLS: [{"symbol": "xyz"}, "xyz"]},
            {CONF_SYMBOLS: [create_symbol_definition("XYZ")]},
        ),
        (
            {
                CONF_SYMBOLS: ["xyz"],
                CONF_SCAN_INTERVAL: 3600,
                CONF_DECIMAL_PLACES: 3,
            },
            {
                CONF_SYMBOLS: [
                    SymbolDefinition("XYZ", scan_interval=timedelta(seconds=3600))
                ],
                CONF_SCAN_INTERVAL: timedelta(hours=1),
                CONF_DECIMAL_PLACES: 3,
            },
        ),
        (
            {
                CONF_SYMBOLS: ["xyz"],
                CONF_SCAN_INTERVAL: "None",
            },
            {
                CONF_SYMBOLS: [SymbolDefinition("XYZ", scan_interval=None)],
                CONF_SCAN_INTERVAL: None,
            },
        ),
        (
            {
                CONF_SYMBOLS: ["xyz"],
                CONF_SCAN_INTERVAL: "none",
            },
            {
                CONF_SYMBOLS: [SymbolDefinition("XYZ", scan_interval=None)],
                CONF_SCAN_INTERVAL: None,
            },
        ),
    ],
)
async def test_setup_refreshes_data_coordinator_and_loads_platform(
    hass, domain_config, expected_partial_config, enable_custom_integrations
):
    """Component setup refreshed data coordinator and loads the platform."""

    # pylint: disable=unused-argument
    # enable_custom_integrations is used

    config = {DOMAIN: domain_config}

    assert await async_setup_component(hass, DOMAIN, config) is True
    await hass.async_block_till_done()

    assert DOMAIN in hass.data

    expected_config = DEFAULT_OPTIONAL_CONFIG.copy()
    expected_config.update(expected_partial_config)

    print(expected_config)
    print(hass.data[DOMAIN][HASS_DATA_CONFIG])
    assert expected_config == hass.data[DOMAIN][HASS_DATA_CONFIG]


@pytest.mark.parametrize(
    "scan_interval",
    [
        (timedelta(-1)),
        (MINIMUM_SCAN_INTERVAL - timedelta(seconds=1)),
        ("None2"),
    ],
)
def test_invalid_scan_interval(hass, scan_interval):
    """Test invalid scan interval."""

    # pylint: disable=unused-argument
    # hass is used

    with pytest.raises(vol.Invalid):
        parse_scan_interval(scan_interval)


async def test_setup_optionally_requests_coordinator_refresh(
    hass, enable_custom_integrations
):
    """Component setup requests data coordinator refresh if it failed to load data."""

    # pylint: disable=unused-argument
    # enable_custom_integrations is used

    with patch(YSUC) as mock_coordinator:
        mock_instance = Mock()
        mock_instance.async_refresh = AsyncMock(return_value=None)
        mock_instance.async_request_refresh = AsyncMock(return_value=None)

        # Mock `last_update_success` to be False which results in a call to `async_request_refresh`
        mock_instance.last_update_success = False

        mock_coordinator.return_value = mock_instance

        assert await async_setup_component(hass, DOMAIN, SAMPLE_CONFIG) is True
        await hass.async_block_till_done()

        assert mock_coordinator.called_with(
            SAMPLE_CONFIG[DOMAIN][CONF_SYMBOLS], hass, DEFAULT_SCAN_INTERVAL
        )
        assert mock_instance.async_refresh.call_count == 1
        assert mock_instance.async_request_refresh.call_count == 1


async def test_refresh_symbols_service(hass, enable_custom_integrations):
    """Test refresh_symbols service callback."""

    # pylint: disable=unused-argument
    # enable_custom_integrations is used

    # Mock the refresh callback `_async_update` for testing
    with patch(
        f"{YSUC}._async_update", AsyncMock(return_value=None)
    ) as mock_async_request_refresh:

        assert await async_setup_component(hass, DOMAIN, SAMPLE_CONFIG) is True
        await hass.async_block_till_done()
        assert mock_async_request_refresh.call_count == 1

        await hass.services.async_call(
            DOMAIN,
            SERVICE_REFRESH,
            {},
            blocking=True,
        )
        await hass.async_block_till_done()

        assert mock_async_request_refresh.call_count == 2


def test_symbol_definition_comparison():
    """Test SymbolDefinition instance comparison."""
    sym1 = SymbolDefinition("ABC")
    sym2 = SymbolDefinition("ABC")
    assert sym1 == sym2
    assert hash(sym1) == hash(sym2)
    assert str(sym1) == str(sym2)


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, None),
        (1642118400, 1642118400),
        ("1646870400", 1646870400),
        ("164687040 0", None),
    ],
)
def test_convert_to_float(value, expected):
    """Tests float conversion."""
    assert convert_to_float(value) == expected
