"""Tests for Yahoo Finance component."""

from datetime import timedelta

from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.async_mock import AsyncMock, Mock, patch

from custom_components.yahoofinance import DEFAULT_SCAN_INTERVAL
from custom_components.yahoofinance.const import (
    CONF_DECIMAL_PLACES,
    CONF_SHOW_TRENDING_ICON,
    CONF_SYMBOLS,
    DEFAULT_CONF_SHOW_TRENDING_ICON,
    DEFAULT_DECIMAL_PLACES,
    DOMAIN,
    HASS_DATA_CONFIG,
    SERVICE_REFRESH,
)

SAMPLE_VALID_CONFIG = {DOMAIN: {CONF_SYMBOLS: ["BABA"]}}
YSUC = "custom_components.yahoofinance.YahooSymbolUpdateCoordinator"


@pytest.mark.parametrize(
    "config, expected_config",
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
            {
                DOMAIN: {
                    CONF_SYMBOLS: ["xyz"],
                    CONF_SCAN_INTERVAL: 3600,
                    CONF_DECIMAL_PLACES: 3,
                }
            },
            {
                CONF_SYMBOLS: ["XYZ"],
                CONF_SCAN_INTERVAL: timedelta(hours=1),
                CONF_DECIMAL_PLACES: 3,
                CONF_SHOW_TRENDING_ICON: DEFAULT_CONF_SHOW_TRENDING_ICON,
            },
        ),
    ],
)
async def test_setup_refreshes_data_coordinator_and_loads_platform(
    hass, config, expected_config
):
    """Component setup refreshed data coordinator and loads the platform."""

    with patch(
        "homeassistant.helpers.discovery.async_load_platform"
    ) as mock_async_load_platform, patch(
        f"{YSUC}.async_refresh", AsyncMock(return_value=None)
    ) as mock_coordinator_async_refresh:

        assert await async_setup_component(hass, DOMAIN, config) is True
        await hass.async_block_till_done()

        assert mock_coordinator_async_refresh.call_count == 1
        assert mock_async_load_platform.call_count == 1

        assert expected_config == hass.data[DOMAIN][HASS_DATA_CONFIG]


async def test_setup_optionally_requests_coordinator_refresh(hass):
    """Component setup requets data coordinator refresh if it failed to load data."""

    # Mock `last_update_success` to be False which results in a call to `async_request_refresh`

    with patch(
        "homeassistant.helpers.discovery.async_load_platform"
    ) as mock_async_load_platform, patch(YSUC) as mock_coordinator:

        mock_instance = Mock()
        mock_instance.async_refresh = AsyncMock(return_value=None)
        mock_instance.async_request_refresh = AsyncMock(return_value=None)
        mock_instance.last_update_success = False

        mock_coordinator.return_value = mock_instance

        assert await async_setup_component(hass, DOMAIN, SAMPLE_VALID_CONFIG) is True
        await hass.async_block_till_done()

        assert mock_instance.async_refresh.call_count == 1
        assert mock_instance.async_request_refresh.call_count == 1
        assert mock_async_load_platform.call_count == 1


async def test_setup_adds_sensor_to_hass(hass, mock_json):
    """Component setup adds sensor to hass."""

    with patch(
        "custom_components.yahoofinance.sensor.YahooFinanceSensor.async_added_to_hass"
    ) as mock_async_added_to_hass, patch(
        f"{YSUC}.get_json", AsyncMock(return_value=mock_json)
    ):
        assert await async_setup_component(hass, DOMAIN, SAMPLE_VALID_CONFIG) is True
        await hass.async_block_till_done()

        assert mock_async_added_to_hass.call_count == 1


async def test_setup_adds_listener_to_coordinator(hass, mock_json):
    """Component setup adds listener to data coordinator."""

    with patch(f"{YSUC}.async_add_listener", Mock()) as mock_async_add_listener, patch(
        f"{YSUC}.get_json", AsyncMock(return_value=mock_json)
    ):
        assert await async_setup_component(hass, DOMAIN, SAMPLE_VALID_CONFIG) is True
        await hass.async_block_till_done()

        assert mock_async_add_listener.call_count == 1


async def test_refresh_service(hass, mock_json):
    """Test service callback."""

    with patch(f"{YSUC}.get_json", AsyncMock(return_value=mock_json)), patch(
        f"{YSUC}.async_request_refresh", AsyncMock(return_value=None)
    ) as mock_async_request_refresh:
        assert await async_setup_component(hass, DOMAIN, SAMPLE_VALID_CONFIG) is True

        await hass.services.async_call(
            DOMAIN,
            SERVICE_REFRESH,
            {},
            blocking=True,
        )
        await hass.async_block_till_done()

        assert mock_async_request_refresh.call_count == 1
