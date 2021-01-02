"""Tests for Yahoo Finance component."""
import copy
import json
import os

from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.async_mock import AsyncMock, Mock, patch

from custom_components.yahoofinance import (
    DEFAULT_SCAN_INTERVAL,
    YahooSymbolUpdateCoordinator,
)
from custom_components.yahoofinance.const import (
    ATTR_CURRENCY_SYMBOL,
    ATTR_TRENDING,
    CONF_DECIMAL_PLACES,
    CONF_SHOW_TRENDING_ICON,
    CONF_SYMBOLS,
    DATA_REGULAR_MARKET_PREVIOUS_CLOSE,
    DATA_REGULAR_MARKET_PRICE,
    DATA_SHORT_NAME,
    DEFAULT_CONF_SHOW_TRENDING_ICON,
    DEFAULT_CURRENCY,
    DEFAULT_CURRENCY_SYMBOL,
    DEFAULT_DECIMAL_PLACES,
    DOMAIN,
    HASS_DATA_CONFIG,
    HASS_DATA_COORDINATOR,
    NUMERIC_DATA_KEYS,
    SERVICE_REFRESH,
    STRING_DATA_KEYS,
)
from custom_components.yahoofinance.sensor import YahooFinanceSensor

SAMPLE_VALID_CONFIG = {
    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
    CONF_DECIMAL_PLACES: DEFAULT_DECIMAL_PLACES,
    CONF_SHOW_TRENDING_ICON: DEFAULT_CONF_SHOW_TRENDING_ICON,
}


def get_json(filename):
    """Load sample JSON."""
    path = os.path.join(os.path.dirname(__file__), filename)
    with open(path, encoding="utf-8") as fptr:
        return fptr.read()


def build_mock_symbol_data(symbol, market_price):
    """Build mock data for a symbol."""
    source_data = {
        DATA_SHORT_NAME: f"Symbol {symbol}",
        DATA_REGULAR_MARKET_PRICE: market_price,
    }
    return YahooSymbolUpdateCoordinator.parse_symbol_data(source_data)


# @pytest.fixture
def build_fake_coordinator(hass, last_update_success, symbol, market_price):
    """Fixture to mock the update data coordinator."""
    coordinator = Mock(
        data={symbol: build_mock_symbol_data(symbol, market_price)},
        hass=hass,
        last_update_success=last_update_success,
    )

    return coordinator


@pytest.mark.parametrize(
    "last_update_success,symbol,market_price,expected_market_price",
    [(True, "XYZ", 12, 12), (False, "^ABC", 0.1221, 0.12), (True, "BOB", 6.156, 6.16)],
)
def test_sensor_data(
    hass, last_update_success, symbol, market_price, expected_market_price
):
    """
    Test sensor status when data corrdinator has data for that symbol
    expected_market_price is the expected rounded market_price
    """

    fake_coordinator = build_fake_coordinator(
        hass, last_update_success, symbol, market_price
    )

    sensor = YahooFinanceSensor(hass, fake_coordinator, symbol, SAMPLE_VALID_CONFIG)

    # Accessing `available` triggers data population
    assert sensor.available is last_update_success

    # state represents the rounded market price
    assert sensor.state == expected_market_price
    assert sensor.name == f"Symbol {symbol}"

    attributes = sensor.device_state_attributes
    # Sensor would be trending up because _previous_close is 0.
    assert attributes[ATTR_TRENDING] == "up"

    # All numeric values besides DATA_REGULAR_MARKET_PRICE should be 0
    for key in NUMERIC_DATA_KEYS:
        if key != DATA_REGULAR_MARKET_PRICE:
            assert attributes[key] == 0

    # Since we did not provide any data so currency should be the default value
    assert sensor.unit_of_measurement == DEFAULT_CURRENCY
    assert attributes[ATTR_CURRENCY_SYMBOL] == DEFAULT_CURRENCY_SYMBOL


@pytest.mark.parametrize(
    "market_price, decimal_places, expected_market_price",
    [
        (12.12645, 2, 12.13),
        (12.12345, 1, 12.1),
        (12.12345, 0, 12),
        (12.12345, -1, 12.12345),
    ],
)
def test_sensor_data_rounded(hass, market_price, decimal_places, expected_market_price):

    symbol = "ABC"
    fake_coordinator = build_fake_coordinator(hass, True, symbol, market_price)

    config = copy.deepcopy(SAMPLE_VALID_CONFIG)
    config[CONF_DECIMAL_PLACES] = decimal_places

    sensor = YahooFinanceSensor(hass, fake_coordinator, symbol, config)

    # Accessing `available` triggers data population
    assert sensor.available is True

    # state represents the rounded market price
    assert sensor.state == expected_market_price


@pytest.mark.parametrize("last_update_success,symbol,market_price", [(True, "XYZ", 12)])
def test_sensor_data_when_coordinator_is_missing_data(
    hass, last_update_success, symbol, market_price
):
    """Test sensor status when data corrdinator does not have data for that symbol"""
    fake_coordinator = build_fake_coordinator(
        hass, last_update_success, symbol, market_price
    )

    # Create a sensor for some other symbol
    symbol_to_test = "ABC"
    sensor = YahooFinanceSensor(
        hass, fake_coordinator, symbol_to_test, SAMPLE_VALID_CONFIG
    )

    # Accessing `available` triggers data population
    assert sensor.available is last_update_success

    assert sensor.state == None

    # Symbol is used as name when thre is no data
    assert sensor.name == symbol_to_test


@pytest.mark.parametrize(
    "market_price,previous_close,show_trending,expected_trend",
    [
        (12, 12, False, "neutral"),
        (12, 12.1, False, "down"),
        (12, 11, False, "up"),
        (12, 12, True, "neutral"),
        (12, 12.1, True, "down"),
        (12, 11, True, "up"),
    ],
)
def test_sensor_trend(
    hass, market_price, previous_close, show_trending, expected_trend
):
    """
    Test sensor trending status.
    """

    symbol = "XYZ"
    fake_coordinator = build_fake_coordinator(hass, True, symbol, market_price)
    fake_coordinator.data[symbol][DATA_REGULAR_MARKET_PREVIOUS_CLOSE] = previous_close

    config = copy.deepcopy(SAMPLE_VALID_CONFIG)
    config[CONF_SHOW_TRENDING_ICON] = show_trending

    sensor = YahooFinanceSensor(hass, fake_coordinator, symbol, config)

    # Accessing `available` triggers data population
    assert sensor.available is True

    # ATTR_TRENDING should always reflect the trending status regarding of CONF_SHOW_TRENDING_ICON
    assert sensor.device_state_attributes[ATTR_TRENDING] == expected_trend

    if show_trending:
        assert sensor.icon == f"mdi:trending-{expected_trend}"
    else:
        currency = sensor.unit_of_measurement
        lower_currency = currency.lower()
        assert sensor.icon == f"mdi:currency-{lower_currency}"


async def test_data_from_json(hass):
    symbol = "BABA"
    json_content = get_json("yahoofinance.json")
    json_data = json.loads(json_content)
    coordinator = YahooSymbolUpdateCoordinator([symbol], hass, DEFAULT_SCAN_INTERVAL)
    coordinator.get_json = AsyncMock(return_value=json_data)
    await coordinator.update()

    sensor = YahooFinanceSensor(hass, coordinator, symbol, SAMPLE_VALID_CONFIG)

    # Accessing `available` triggers data population
    assert sensor.available is True

    attributes = sensor.device_state_attributes

    assert sensor.state == 232.73
    assert attributes["regularMarketChange"] == -5.66
    assert attributes["twoHundredDayAverageChangePercent"] == -0.13
