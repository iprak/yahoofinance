"""Tests for Yahoo Finance component."""

import asyncio

from homeassistant.helpers.update_coordinator import UpdateFailed
import pytest
from pytest_homeassistant_custom_component.async_mock import AsyncMock, Mock

from custom_components.yahoofinance import (
    DEFAULT_SCAN_INTERVAL,
    YahooSymbolUpdateCoordinator,
)

TEST_SYMBOL = "BABA"


@pytest.mark.parametrize(
    "parsed_json, message",
    [
        (None, "No data"),
        ({}, "quoteResponse missing"),
        ({"quoteResponse": {"error": "fake error"}}, "error present"),
        ({"quoteResponse": {}}, "result missing"),
        ({"quoteResponse": {"result": None}}, "result is None"),
    ],
)
async def test_incomplete_json(hass, parsed_json, message):
    """Test invalid json parsing. Existing data is not updated."""
    coordinator = YahooSymbolUpdateCoordinator(None, hass, DEFAULT_SCAN_INTERVAL)
    coordinator.get_json = AsyncMock(return_value=parsed_json)

    existing_data = {}
    coordinator.data = existing_data
    print(message)

    with pytest.raises(UpdateFailed):
        assert await coordinator.update()

    assert coordinator.data is existing_data
    assert coordinator.last_update_success is False


@pytest.mark.parametrize(
    "raised_exception",
    [
        (Exception),
        (asyncio.TimeoutError),
    ],
)
async def test_json_download_failure(hass, raised_exception):
    """Test exceptions generated while downloading json. Existing data is not updated."""

    coordinator = YahooSymbolUpdateCoordinator(
        [TEST_SYMBOL], hass, DEFAULT_SCAN_INTERVAL
    )
    coordinator.websession.get = AsyncMock(side_effect=raised_exception)

    existing_data = {}
    coordinator.data = existing_data

    with pytest.raises(UpdateFailed):
        assert await coordinator.update()

    assert coordinator.data is existing_data
    assert coordinator.last_update_success is False


async def test_successful_data_parsing(hass, mock_json):
    """Tests successful data parsing."""

    coordinator = YahooSymbolUpdateCoordinator(
        [TEST_SYMBOL], hass, DEFAULT_SCAN_INTERVAL
    )

    mock_response = Mock()
    mock_response.json = AsyncMock(return_value=mock_json)

    coordinator.websession.get = AsyncMock(return_value=mock_response)

    await coordinator.update()

    assert coordinator.data is not None
    assert TEST_SYMBOL in coordinator.data
    assert coordinator.last_update_success is True
