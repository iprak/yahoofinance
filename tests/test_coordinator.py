"""Tests for Yahoo Finance component."""

import asyncio
import random

import pytest
from pytest_homeassistant_custom_component.async_mock import AsyncMock, Mock

from custom_components.yahoofinance import (
    DEFAULT_SCAN_INTERVAL,
    YahooSymbolUpdateCoordinator,
)
from custom_components.yahoofinance.const import DATA_REGULAR_MARKET_PRICE

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
    """Existing data is not updated if JSON is invalid."""

    print(message)
    coordinator = YahooSymbolUpdateCoordinator(None, hass, DEFAULT_SCAN_INTERVAL)
    coordinator.get_json = AsyncMock(return_value=parsed_json)

    existing_data = {TEST_SYMBOL: {DATA_REGULAR_MARKET_PRICE: random.random()}}
    coordinator.data = existing_data

    # last_update_success is initially True
    assert coordinator.last_update_success is True

    await coordinator.async_refresh()
    await hass.async_block_till_done()

    # Data was invalid, existing data was left unchanged and last_update_success becomes False
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
    """Existing data is not updated if exception enocuntered while downloading json."""

    coordinator = YahooSymbolUpdateCoordinator(
        [TEST_SYMBOL], hass, DEFAULT_SCAN_INTERVAL
    )
    coordinator.websession.get = AsyncMock(side_effect=raised_exception)

    existing_data = {TEST_SYMBOL: {DATA_REGULAR_MARKET_PRICE: random.random()}}
    coordinator.data = existing_data

    await coordinator.async_refresh()
    await hass.async_block_till_done()

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

    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert coordinator.data is not None
    assert TEST_SYMBOL in coordinator.data
    assert coordinator.last_update_success is True
