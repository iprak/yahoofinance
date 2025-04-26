"""Tests for Yahoo Finance component."""

import copy
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from custom_components.yahoofinance import (
    DEFAULT_SCAN_INTERVAL,
    YahooSymbolUpdateCoordinator,
)
from custom_components.yahoofinance.const import (
    ATTR_CURRENCY_SYMBOL,
    ATTR_TRENDING,
    CONF_DECIMAL_PLACES,
    CONF_INCLUDE_FIFTY_DAY_VALUES,
    CONF_INCLUDE_POST_VALUES,
    CONF_INCLUDE_PRE_VALUES,
    CONF_INCLUDE_TWO_HUNDRED_DAY_VALUES,
    CONF_SHOW_CURRENCY_SYMBOL_AS_UNIT,
    CONF_SHOW_TRENDING_ICON,
    CONF_SYMBOLS,
    DATA_CURRENCY_SYMBOL,
    DATA_DIVIDEND_DATE,
    DATA_POST_MARKET_TIME,
    DATA_PRE_MARKET_TIME,
    DATA_REGULAR_MARKET_PREVIOUS_CLOSE,
    DATA_REGULAR_MARKET_PRICE,
    DATA_REGULAR_MARKET_TIME,
    DATA_SHORT_NAME,
    DEFAULT_CONF_DECIMAL_PLACES,
    DEFAULT_CONF_INCLUDE_FIFTY_DAY_VALUES,
    DEFAULT_CONF_INCLUDE_POST_VALUES,
    DEFAULT_CONF_INCLUDE_PRE_VALUES,
    DEFAULT_CONF_INCLUDE_TWO_HUNDRED_DAY_VALUES,
    DEFAULT_CONF_SHOW_CURRENCY_SYMBOL_AS_UNIT,
    DEFAULT_CONF_SHOW_TRENDING_ICON,
    DEFAULT_CURRENCY,
    DEFAULT_CURRENCY_SYMBOL,
    DOMAIN,
    HASS_DATA_CONFIG,
    HASS_DATA_COORDINATORS,
    NUMERIC_DATA_GROUPS,
)
from custom_components.yahoofinance.data import SymbolDefinition
from custom_components.yahoofinance.sensor import (
    YahooFinanceSensor,
    async_setup_platform,
)
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant

from . import TEST_SYMBOL

DEFAULT_OPTIONAL_CONFIG = {
    CONF_DECIMAL_PLACES: DEFAULT_CONF_DECIMAL_PLACES,
    CONF_INCLUDE_FIFTY_DAY_VALUES: DEFAULT_CONF_INCLUDE_FIFTY_DAY_VALUES,
    CONF_INCLUDE_POST_VALUES: DEFAULT_CONF_INCLUDE_POST_VALUES,
    CONF_INCLUDE_PRE_VALUES: DEFAULT_CONF_INCLUDE_PRE_VALUES,
    CONF_INCLUDE_TWO_HUNDRED_DAY_VALUES: DEFAULT_CONF_INCLUDE_TWO_HUNDRED_DAY_VALUES,
    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
    CONF_SHOW_TRENDING_ICON: DEFAULT_CONF_SHOW_TRENDING_ICON,
    CONF_SHOW_CURRENCY_SYMBOL_AS_UNIT: DEFAULT_CONF_SHOW_CURRENCY_SYMBOL_AS_UNIT,
    "numeric_values_to_include": ["default"],
}

YSUC = "custom_components.yahoofinance.YahooSymbolUpdateCoordinator"


def build_mock_symbol_data(
    symbol,
    market_price,
    currency="USD",
):
    """Build mock data for a symbol."""
    source_data = {
        DATA_CURRENCY_SYMBOL: currency,
        DATA_SHORT_NAME: f"Symbol {symbol}",
        DATA_REGULAR_MARKET_PRICE: market_price,
    }
    return YahooSymbolUpdateCoordinator.parse_symbol_data(source_data)


def build_mock_coordinator(
    hass: HomeAssistant, last_update_success, symbol, market_price
):
    """Build a mock data coordinator."""
    return Mock(
        data={symbol: build_mock_symbol_data(symbol, market_price)},
        hass=hass,
        last_update_success=last_update_success,
    )


def build_mock_coordinator_for_conversion(
    hass: HomeAssistant,
    symbol,
    market_price,
    currency,
    target_currency,
    target_market_price,
):
    """Build a mock data coordinator with conversion data."""

    target_symbol = f"{currency}{target_currency}=X"
    return Mock(
        data={
            symbol: build_mock_symbol_data(symbol, market_price),
            target_symbol: build_mock_symbol_data(
                target_symbol, target_market_price, target_currency
            ),
        },
        hass=hass,
        last_update_success=True,
    )


def install_coordinator(hass: HomeAssistant, coordinator) -> None:
    """Install the coordinator into HASS_DATA_COORDINATORS store."""
    hass.data[DOMAIN] = {HASS_DATA_COORDINATORS: {DEFAULT_SCAN_INTERVAL: coordinator}}


async def test_setup_platform(hass: HomeAssistant) -> None:
    """Test platform setup."""

    async_add_entities = MagicMock()
    mock_coordinator = build_mock_coordinator(hass, True, TEST_SYMBOL, 12)
    mock_coordinators = {DEFAULT_SCAN_INTERVAL: mock_coordinator}

    config = copy.deepcopy(DEFAULT_OPTIONAL_CONFIG)
    config[CONF_SYMBOLS] = [
        SymbolDefinition(TEST_SYMBOL, scan_interval=DEFAULT_SCAN_INTERVAL)
    ]

    hass.data = {
        DOMAIN: {
            HASS_DATA_COORDINATORS: mock_coordinators,
            HASS_DATA_CONFIG: config,
        }
    }

    await async_setup_platform(hass, None, async_add_entities, None)
    assert async_add_entities.called


@pytest.mark.parametrize(
    ("last_update_success", "symbol", "market_price", "expected_market_price"),
    [(True, "XYZ", 12, 12), (False, "^ABC", 0.1221, 0.12), (True, "BOB", 6.156, 6.16)],
)
def test_sensor_creation(
    hass: HomeAssistant,
    last_update_success,
    symbol,
    market_price,
    expected_market_price,
) -> None:
    """Test sensor status based on the expected_market_price."""

    mock_coordinator = build_mock_coordinator(
        hass, last_update_success, symbol, market_price
    )

    sensor = YahooFinanceSensor(
        hass, mock_coordinator, SymbolDefinition(symbol), DEFAULT_OPTIONAL_CONFIG
    )

    # Force sensor update from coordinator
    sensor.update_properties()

    assert sensor.available is last_update_success

    # state represents the rounded market price
    assert sensor.state == expected_market_price
    assert sensor.name == f"Symbol {symbol}"

    attributes = sensor.extra_state_attributes
    # Sensor would be trending up because _previous_close is 0.
    assert attributes[ATTR_TRENDING] == "up"

    # All numeric values besides DATA_REGULAR_MARKET_PRICE should be 0
    for data_group in NUMERIC_DATA_GROUPS.values():
        for value in data_group:
            key = value[0]
            if (
                (key != DATA_REGULAR_MARKET_PRICE)  # noqa: PLR1714
                and (key != DATA_DIVIDEND_DATE)
                and (key != DATA_REGULAR_MARKET_TIME)
                and (key != DATA_PRE_MARKET_TIME)
                and (key != DATA_POST_MARKET_TIME)
            ):
                assert attributes[key] == 0

    # Since we did not provide any data so currency should be the default value
    assert sensor.unit_of_measurement == DEFAULT_CURRENCY
    assert attributes[ATTR_CURRENCY_SYMBOL] == DEFAULT_CURRENCY_SYMBOL

    assert sensor.should_poll is False


@pytest.mark.parametrize(
    ("market_price", "decimal_places", "expected_market_price"),
    [
        (12.12645, 2, 12.13),
        (12.12345, 1, 12.1),
        (12.12345, 0, 12),
        (12.12345, -1, 12.12345),
    ],
)
def test_sensor_decimal_placs(
    hass: HomeAssistant, market_price, decimal_places, expected_market_price
) -> None:
    """Tests numeric value rounding."""

    symbol = "XYZ"
    mock_coordinator = build_mock_coordinator(hass, True, symbol, market_price)

    config = copy.deepcopy(DEFAULT_OPTIONAL_CONFIG)
    config[CONF_DECIMAL_PLACES] = decimal_places

    sensor = YahooFinanceSensor(
        hass, mock_coordinator, SymbolDefinition(symbol), config
    )

    sensor.update_properties()

    assert sensor.available is True

    # state represents the rounded market price
    assert sensor.state == expected_market_price


@pytest.mark.parametrize(
    ("last_update_success", "symbol", "market_price"), [(True, "XYZ", 12)]
)
def test_sensor_data_when_coordinator_is_missing_symbol_data(
    hass: HomeAssistant, last_update_success, symbol, market_price
) -> None:
    """Test sensor status when data coordinator does not have data for that symbol."""

    mock_coordinator = build_mock_coordinator(
        hass, last_update_success, symbol, market_price
    )

    # Create a sensor for some other symbol
    symbol_to_test = "ABC"
    sensor = YahooFinanceSensor(
        hass,
        mock_coordinator,
        SymbolDefinition(symbol_to_test),
        DEFAULT_OPTIONAL_CONFIG,
    )

    sensor.update_properties()

    # Coordinator does not have data for this symbol
    assert sensor.available is False
    assert sensor.state is None
    # Symbol is used as name when there is no data
    assert sensor.name == symbol_to_test


def test_sensor_data_when_coordinator_returns_none(hass: HomeAssistant) -> None:
    """Test sensor status when data coordinator does not have any data."""

    symbol = "XYZ"
    mock_coordinator = Mock(
        data=None,
        hass=hass,
        last_update_success=False,
    )

    sensor = YahooFinanceSensor(
        hass, mock_coordinator, SymbolDefinition(symbol), DEFAULT_OPTIONAL_CONFIG
    )

    sensor.update_properties()

    assert sensor.available is False

    assert sensor.state is None
    # Since we do not have data so the name will be the symbol
    assert sensor.name == symbol


async def test_sensor_update_calls_coordinator(hass: HomeAssistant) -> None:
    """Test sensor data update."""

    symbol = "XYZ"
    mock_coordinator = build_mock_coordinator(hass, True, symbol, None)
    mock_coordinator.async_request_refresh = AsyncMock(return_value=None)
    sensor = YahooFinanceSensor(
        hass, mock_coordinator, SymbolDefinition(symbol), DEFAULT_OPTIONAL_CONFIG
    )

    await sensor.async_update()
    assert mock_coordinator.async_request_refresh.call_count == 1


@pytest.mark.parametrize(
    ("market_price", "previous_close", "show_trending", "expected_trend"),
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
    hass: HomeAssistant, market_price, previous_close, show_trending, expected_trend
) -> None:
    """Test sensor trending status."""

    symbol = "XYZ"
    mock_coordinator = build_mock_coordinator(hass, True, symbol, market_price)
    mock_coordinator.data[symbol][DATA_REGULAR_MARKET_PREVIOUS_CLOSE] = previous_close

    config = copy.deepcopy(DEFAULT_OPTIONAL_CONFIG)
    config[CONF_SHOW_TRENDING_ICON] = show_trending

    sensor = YahooFinanceSensor(
        hass, mock_coordinator, SymbolDefinition(symbol), config
    )

    sensor.update_properties()

    assert sensor.available is True

    # ATTR_TRENDING should always reflect the trending status regarding of CONF_SHOW_TRENDING_ICON
    assert sensor.extra_state_attributes[ATTR_TRENDING] == expected_trend

    if show_trending:
        assert sensor.icon == f"mdi:trending-{expected_trend}"
    else:
        currency = sensor.unit_of_measurement
        lower_currency = currency.lower()
        assert sensor.icon == f"mdi:currency-{lower_currency}"


def test_sensor_trending_state_is_not_populate_if_previous_closing_missing(
    hass: HomeAssistant,
) -> None:
    """The trending state is None if _previous_close is None for some reason."""

    symbol = "XYZ"
    mock_coordinator = build_mock_coordinator(hass, True, symbol, 12)

    # Force update _previous_close to None
    mock_coordinator.data[symbol][DATA_REGULAR_MARKET_PREVIOUS_CLOSE] = None

    config = copy.deepcopy(DEFAULT_OPTIONAL_CONFIG)
    config[CONF_SHOW_TRENDING_ICON] = True

    sensor = YahooFinanceSensor(
        hass, mock_coordinator, SymbolDefinition(symbol), config
    )

    sensor.update_properties()

    assert sensor.available is True

    # ATTR_TRENDING should always reflect the trending status regarding of CONF_SHOW_TRENDING_ICON
    assert (ATTR_TRENDING in sensor.extra_state_attributes) is False

    # icon is based on the currency
    currency = sensor.unit_of_measurement
    lower_currency = currency.lower()
    assert sensor.icon == f"mdi:currency-{lower_currency}"


async def test_data_from_json(
    hass: HomeAssistant, mock_json, mocked_crumb_coordinator
) -> None:
    """Tests data update all the way from from json."""
    symbol = TEST_SYMBOL
    coordinator = YahooSymbolUpdateCoordinator(
        [symbol], hass, DEFAULT_SCAN_INTERVAL, mocked_crumb_coordinator
    )
    coordinator.get_json = AsyncMock(return_value=mock_json)

    await coordinator.async_refresh()
    await hass.async_block_till_done()

    sensor = YahooFinanceSensor(
        hass, coordinator, SymbolDefinition(symbol), DEFAULT_OPTIONAL_CONFIG
    )

    sensor.update_properties()

    assert sensor.available is True

    attributes = sensor.extra_state_attributes

    assert sensor.state == 232.73
    assert attributes["regularMarketChange"] == -5.66
    assert attributes["twoHundredDayAverageChangePercent"] == -12.61  # from -0.12609957


@pytest.mark.parametrize(
    ("value", "conversion", "expected"),
    [(123.5, 1, 123.5), (None, 1, None), (123.5, None, 123.5)],
)
def test_safe_convert(value, conversion, expected) -> None:
    """Test value conversion."""
    assert YahooFinanceSensor.safe_convert(value, conversion) == expected


def test_conversion(hass: HomeAssistant) -> None:
    """Numeric values get multiplied based on conversion currency."""

    symbol = "XYZ"
    mock_coordinator = build_mock_coordinator_for_conversion(
        hass, symbol, 12, "USD", "CHF", 1.5
    )

    # Force update _previous_close to None
    mock_coordinator.data[symbol][DATA_REGULAR_MARKET_PREVIOUS_CLOSE] = None
    install_coordinator(hass, mock_coordinator)

    sensor = YahooFinanceSensor(
        hass,
        mock_coordinator,
        SymbolDefinition(symbol, target_currency="CHF"),
        DEFAULT_OPTIONAL_CONFIG,
    )

    sensor.update_properties()

    assert sensor.available is True
    assert sensor.state == (12 * 1.5)


def test_conversion_requests_additional_data_from_coordinator(
    hass: HomeAssistant,
) -> None:
    """Numeric values get multiplied based on conversion currency."""

    symbol = "XYZ"
    mock_coordinator = build_mock_coordinator(hass, True, symbol, 12)

    # Force update _previous_close to None
    mock_coordinator.data[symbol][DATA_REGULAR_MARKET_PREVIOUS_CLOSE] = None
    install_coordinator(hass, mock_coordinator)

    sensor = YahooFinanceSensor(
        hass,
        mock_coordinator,
        SymbolDefinition(symbol, target_currency="EUR"),
        DEFAULT_OPTIONAL_CONFIG,
    )

    with patch.object(mock_coordinator, "add_symbol") as mock_add_symbol:
        sensor.update_properties()

        # available remains False till the conversion symbol gets loaded
        assert sensor.available is False

        assert mock_add_symbol.call_count == 1


def test_conversion_not_attempted_if_target_currency_same(hass: HomeAssistant) -> None:
    """No conversion is attempted if target curency is the same as symbol currency."""

    symbol = "XYZ"
    mock_coordinator = build_mock_coordinator(hass, True, symbol, 12)

    # Force update _previous_close to None
    mock_coordinator.data[symbol][DATA_REGULAR_MARKET_PREVIOUS_CLOSE] = None

    sensor = YahooFinanceSensor(
        hass,
        mock_coordinator,
        SymbolDefinition(symbol, target_currency="USD"),
        DEFAULT_OPTIONAL_CONFIG,
    )

    with patch.object(mock_coordinator, "add_symbol") as mock_add_symbol:
        sensor.update_properties()

        assert sensor.available is True

        # The mock data has currency USD and target is USD too.
        assert mock_add_symbol.call_count == 0


@pytest.mark.parametrize(
    ("epoch_date", "return_format", "expected_datetime"),
    [
        (None, "date", None),
        (1642118400, "date", "2022-01-14"),
        (1646870400, "date", "2022-03-10"),
        ("1646870400", "date", "2022-03-10"),
        ("164687040 0", "date", None),
        (1642118453, "datetime", "2022-01-14T00:00:53+00:00"),
        (1646878750, "datetime", "2022-03-10T02:19:10+00:00"),
        ("1646878750", "datetime", "2022-03-10T02:19:10+00:00"),
        ("164687040 0", "datetime", None),
        (0, "date", 0),
        (0, "datetime", 0),
    ],
)
def test_convert_timestamp_to_datetime(
    epoch_date, return_format, expected_datetime
) -> None:
    """Test converting Epoch times to datetime and return date or datetime based on return format."""
    assert (
        YahooFinanceSensor.convert_timestamp_to_datetime(epoch_date, return_format)
        == expected_datetime
    )
