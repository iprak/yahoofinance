"""Tests for Yahoo Finance component."""

import asyncio
from datetime import timedelta
from http import HTTPStatus
import random
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest

from custom_components.yahoofinance import (
    DEFAULT_SCAN_INTERVAL,
    YahooSymbolUpdateCoordinator,
    coordinator,
)
from custom_components.yahoofinance.const import BASE, DATA_REGULAR_MARKET_PRICE
from custom_components.yahoofinance.coordinator import (
    FAILURE_ASYNC_REQUEST_REFRESH,
    CrumbCoordinator,
)

from . import TEST_CRUMB, TEST_SYMBOL
from .conftest import create_mock_coordinator

TEST_SYMBOL2 = "RBOT.L"
SECOND_TEST_SYMBOL = "^SSMI"
YSUC = "custom_components.yahoofinance.YahooSymbolUpdateCoordinator"


@pytest.mark.parametrize(
    ("parsed_json", "message"),
    [
        (None, "No data"),
        ({}, "quoteResponse missing"),
        ({"quoteResponse": {"error": "fake error"}}, "error present"),
        ({"quoteResponse": {}}, "result missing"),
        ({"quoteResponse": {"result": None}}, "result is None"),
    ],
)
async def test_incomplete_json(
    hass, parsed_json, message, mocked_crumb_coordinator
) -> None:
    """Existing data is not updated if JSON is invalid."""

    mock_coordinator = YahooSymbolUpdateCoordinator(
        None, hass, DEFAULT_SCAN_INTERVAL, mocked_crumb_coordinator
    )
    mock_coordinator.get_json = AsyncMock(return_value=parsed_json)

    existing_data = {TEST_SYMBOL: {DATA_REGULAR_MARKET_PRICE: random.random()}}
    mock_coordinator.data = existing_data

    # last_update_success is initially True
    assert mock_coordinator.last_update_success is True

    await mock_coordinator.async_refresh()
    await hass.async_block_till_done()

    # Data was invalid, existing data was left unchanged and last_update_success becomes False
    assert mock_coordinator.data is existing_data
    assert mock_coordinator.last_update_success is False


@pytest.mark.parametrize(
    "raised_exception",
    [
        (Exception),
        (aiohttp.ClientError),
        (asyncio.TimeoutError),
    ],
)
async def test_json_download_failure(
    hass, raised_exception, mocked_crumb_coordinator
) -> None:
    """Existing data is not updated if exception encountered while downloading json."""

    mock_coordinator = YahooSymbolUpdateCoordinator(
        [TEST_SYMBOL], hass, DEFAULT_SCAN_INTERVAL, mocked_crumb_coordinator
    )
    mock_coordinator.websession.get = AsyncMock(side_effect=raised_exception)

    existing_data = {TEST_SYMBOL: {DATA_REGULAR_MARKET_PRICE: random.random()}}
    mock_coordinator.data = existing_data

    mock_coordinator_listener = Mock()
    mock_coordinator.async_add_listener(mock_coordinator_listener)

    with patch.object(mock_coordinator, "_schedule_refresh") as mock_schedule_refresh:
        await mock_coordinator.async_refresh()
        await hass.async_block_till_done()

        assert mock_coordinator.data is existing_data
        assert mock_coordinator.last_update_success is False

        assert len(mock_coordinator_listener.mock_calls) == 1
        assert len(mock_schedule_refresh.mock_calls) == 1


async def test_successful_data_parsing(
    hass, mocked_crumb_coordinator, mock_json
) -> None:
    """Tests successful data parsing."""

    mock_coordinator = create_mock_coordinator(hass, mocked_crumb_coordinator)
    mock_coordinator.get_json = AsyncMock(return_value=mock_json)

    await mock_coordinator.async_refresh()
    await hass.async_block_till_done()

    assert mock_coordinator.data is not None
    assert TEST_SYMBOL in mock_coordinator.data
    assert mock_coordinator.last_update_success is True


async def test_add_symbol(hass, mocked_crumb_coordinator) -> None:
    """Add symbol for load."""
    mock_coordinator = YahooSymbolUpdateCoordinator(
        [], hass, DEFAULT_SCAN_INTERVAL, mocked_crumb_coordinator
    )

    with patch("homeassistant.helpers.event.async_call_later") as mock_call_later:
        assert mock_coordinator.add_symbol(TEST_SYMBOL) is True
        assert TEST_SYMBOL in mock_coordinator.get_symbols()
        assert len(mock_call_later.mock_calls) == 1


async def test_add_symbol_existing(hass, mocked_crumb_coordinator) -> None:
    """Test check for existing symbols."""
    mock_coordinator = YahooSymbolUpdateCoordinator(
        [TEST_SYMBOL], hass, DEFAULT_SCAN_INTERVAL, mocked_crumb_coordinator
    )
    assert mock_coordinator.add_symbol(TEST_SYMBOL) is False


async def test_update_interval_when_update_fails(
    hass, mocked_crumb_coordinator
) -> None:
    """Update interval for the next async_track_point_in_utc_time call."""
    mock_coordinator = YahooSymbolUpdateCoordinator(
        [TEST_SYMBOL], hass, DEFAULT_SCAN_INTERVAL, mocked_crumb_coordinator
    )

    # update_interval is DEFAULT_SCAN_INTERVAL
    assert mock_coordinator.get_next_update_interval() is DEFAULT_SCAN_INTERVAL

    # update_interval is FAILURE_ASYNC_REQUEST_REFRESH if update failed
    mock_coordinator.last_update_success = False
    assert mock_coordinator.get_next_update_interval() == timedelta(
        seconds=FAILURE_ASYNC_REQUEST_REFRESH
    )


async def test_update_when_update_is_disabled(hass, mocked_crumb_coordinator) -> None:
    """No update is performed if update_interval is None."""

    mock_coordinator = YahooSymbolUpdateCoordinator(
        [TEST_SYMBOL], hass, None, mocked_crumb_coordinator
    )

    mock_coordinator.last_update_success = False
    assert mock_coordinator.get_next_update_interval() == timedelta(
        seconds=FAILURE_ASYNC_REQUEST_REFRESH
    )

    mock_coordinator.last_update_success = True
    assert mock_coordinator.get_next_update_interval() is None


@pytest.mark.parametrize(
    ("symbol", "symbol_data", "expected_symbol"),
    [
        (None, None, None),
        ("TEST", None, "TEST"),  # Not conversion symbol
        ("TEST", {"shortName": "USD/EUR"}, "TEST"),  # Not conversion symbol
        ("USDEUR=X", {"shortName": "USD/EUR"}, "USDEUR=X"),  # No change necessary
        ("EUR=X", {"shortName": "USD/EUR"}, "USDEUR=X"),  # Missing USD
        (
            "SYMBOL=X",
            {"shortName": "USD/EUR"},
            "USDEUR=X",
        ),  # symbol does not match shortName at all
        ("EUR=X", {"shortName": "USDEUR"}, "EUR=X"),  # shortName is invalid
        ("EUR=X", {"shortName": "USD/"}, "EUR=X"),  # shortName is invalid
        ("EUR=X", {"shortName": "/EUR"}, "EUR=X"),  # shortName is invalid
    ],
)
async def test_fix_conversion_symbol(
    hass, symbol, symbol_data, expected_symbol, mocked_crumb_coordinator
) -> None:
    """Test conversion symbol correction."""
    mock_coordinator = YahooSymbolUpdateCoordinator(
        [TEST_SYMBOL], hass, None, mocked_crumb_coordinator
    )
    assert (
        mock_coordinator.fix_conversion_symbol(symbol, symbol_data) == expected_symbol
    )


@pytest.mark.parametrize(
    ("symbols", "result", "expected_error_encountered", "expected_conversion_count"),
    [
        (  # Symbol missing in result
            [TEST_SYMBOL, TEST_SYMBOL2],
            [{"symbol": TEST_SYMBOL}],
            True,
            0,
        ),
        (  # All symbols present in result
            [TEST_SYMBOL, TEST_SYMBOL2],
            [
                {"symbol": TEST_SYMBOL},
                {"symbol": TEST_SYMBOL2},
            ],
            False,
            0,
        ),
        (["USDEUR=X"], [{"symbol": "EUR=X"}], False, 1),  # Symbol conversion fix test
        (  # Multiple conversion symbol fix test
            [
                TEST_SYMBOL,
                "USDEUR=X",
                "USDCHF=X",
            ],
            [{"symbol": "EUR=X"}, {"symbol": TEST_SYMBOL}, {"symbol": "CHF=X"}],
            False,
            2,
        ),
        (  # Symbol conversion missing test
            ["USDCHF=X"],
            [{"symbol": "EUR=X"}],
            True,
            1,
        ),
    ],
)
async def test_process_json_result(
    hass,
    symbols,
    result,
    expected_error_encountered,
    expected_conversion_count,
    mocked_crumb_coordinator,
) -> None:
    """No update is performed if update_interval is None."""
    mock_coordinator = YahooSymbolUpdateCoordinator(
        symbols, hass, None, mocked_crumb_coordinator
    )

    def prefix_conversion_symbol(symbol: str, symbol_data: any):
        return f"USD{symbol}"

    mock_fix_conversion_symbol = Mock(side_effect=prefix_conversion_symbol)
    mock_coordinator.fix_conversion_symbol = mock_fix_conversion_symbol

    (error_encountered, data) = mock_coordinator.process_json_result(result)

    assert len(mock_fix_conversion_symbol.mock_calls) == expected_conversion_count
    assert error_encountered is expected_error_encountered
    assert data is not None


async def test_logging_when_process_json_result_reports_error(
    hass, mock_json, mocked_crumb_coordinator
) -> None:
    """Tests call to logger.info() when process_json_result reports an error."""
    mock_coordinator = YahooSymbolUpdateCoordinator(
        [TEST_SYMBOL], hass, DEFAULT_SCAN_INTERVAL, mocked_crumb_coordinator
    )

    mock_response = Mock()
    mock_response.status = HTTPStatus.NO_CONTENT
    mock_response.json = AsyncMock(return_value=mock_json)

    mock_coordinator.websession.get = AsyncMock(return_value=mock_response)
    mock_coordinator.process_json_result = Mock(return_value=(True, None))

    with patch.object(coordinator, "_LOGGER") as mock_logger:
        await mock_coordinator.async_refresh()
        await hass.async_block_till_done()

        assert mock_logger.error.call_count == 1


def test_crumbcoordinator_ctor(hass) -> None:
    """Test CrumbCoordinator contructor."""
    instance = CrumbCoordinator(hass)
    assert instance.cookies is None
    assert instance.crumb is None


def test_crumbcoordinator_reset(hass) -> None:
    """Test CrumbCoordinator contructor."""
    instance = CrumbCoordinator(hass)
    instance.cookies = "cookies"
    instance.crumb = "crumb"

    instance.reset()
    assert instance.cookies is None
    assert instance.crumb is None


async def test_build_request_url(hass, mocked_crumb_coordinator) -> None:
    """Test build_request_url."""

    mock_coordinator = YahooSymbolUpdateCoordinator(
        [TEST_SYMBOL], hass, DEFAULT_SCAN_INTERVAL, mocked_crumb_coordinator
    )
    # print(await mock_coordinator.build_request_url())
    assert (
        await mock_coordinator.build_request_url()
        == BASE + TEST_SYMBOL + "&crumb=" + TEST_CRUMB
    )


def test_get_finance_error_code() -> None:
    """Test get_finance_error_code."""
    assert YahooSymbolUpdateCoordinator.get_finance_error_code(None) is None
    assert YahooSymbolUpdateCoordinator.get_finance_error_code({}) is None
    assert YahooSymbolUpdateCoordinator.get_finance_error_code({"finance": {}}) is None
    assert YahooSymbolUpdateCoordinator.get_finance_error_code(
        {"finance": {"error": {"code": "code", "description": "description"}}}
    ) == ("code", "description")
