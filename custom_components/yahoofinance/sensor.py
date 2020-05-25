"""
A component which presents Yahoo Finance stock quotes.
https://github.com/custom-components/sensor.weatheralerts
"""

from datetime import timedelta
import logging
import voluptuous as vol
import async_timeout

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import ATTR_ATTRIBUTION, CONF_SCAN_INTERVAL
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import Entity, async_generate_entity_id
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    BASE,
    CONF_SYMBOLS,
    DOMAIN,
    ICON,
)

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Data provided by Yahoo Finance"
ATTR_FIFTY_DAY_AVERAGE = "fiftyDayAverage"
ATTR_PREVIOUS_CLOSE = "previousClose"
ATTR_FIFTY_DAY_SYMBOL = "symbol"
ENTITY_ID_FORMAT = DOMAIN + ".{}"

SCAN_INTERVAL = timedelta(hours=6)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_SYMBOLS): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL): cv.time_period,
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Yahoo Finance sensors."""
    symbols = config.get(CONF_SYMBOLS, [])
    coordinator = YahooSymbolUpdateCoordinator(
        symbols, hass, config.get(CONF_SCAN_INTERVAL)
    )
    await coordinator.async_refresh()

    sensors = []
    for symbol in symbols:
        sensors.append(YahooFinanceSensor(coordinator, symbol, hass))

    # The True param fetches data first time before being written to HA
    async_add_entities(sensors, False)
    _LOGGER.info("Added sensors for %s", symbols)


class YahooFinanceSensor(Entity):
    """Defines a Yahoo finance sensor"""

    _symbol = None
    _shortName = None
    _fiftyDayAverage = None

    def __init__(self, coordinator, symbol, hass) -> None:
        """Initialize the sensor."""
        self._symbol = symbol
        self._coordinator = coordinator
        self._unit_of_measurement = "USD"
        self.entity_id = async_generate_entity_id(ENTITY_ID_FORMAT, symbol, hass=hass)
        _LOGGER.debug("Created %s", self.entity_id)

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        if self._shortName is not None:
            return self._shortName
        else:
            return self._symbol

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            ATTR_FIFTY_DAY_SYMBOL: self._symbol,
            ATTR_FIFTY_DAY_AVERAGE: self._fiftyDayAverage,
            ATTR_PREVIOUS_CLOSE: self._previousClose,
        }

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend, if any."""
        return ICON

    def fetch_data(self) -> None:
        data = self._coordinator.data
        if data is None:
            return

        symbolData = data[self._symbol]
        if symbolData is None:
            return

        self._shortName = symbolData["shortName"]
        self._state = symbolData["regularMarketPrice"]
        self._fiftyDayAverage = symbolData["fiftyDayAverage"]
        self._previousClose = symbolData["regularMarketPreviousClose"]

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        self.fetch_data()
        return self._coordinator.last_update_success

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        self._coordinator.async_add_listener(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from hass."""
        self._coordinator.async_remove_listener(self.async_write_ha_state)

    async def async_update(self) -> None:
        """Update symbol data."""
        await self._coordinator.async_request_refresh()


class YahooSymbolUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage Yahoo finance data update."""

    def __init__(self, symbols, hass, update_interval) -> None:
        """Initialize."""
        self._symbols = symbols
        self.data = None
        self.loop = hass.loop
        self.websession = async_get_clientsession(hass)

        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=update_interval,
        )

    async def _async_update_data(self):
        """Update data."""
        try:
            await self.update()
        except () as error:
            raise UpdateFailed(error)
        return self.data

    async def get_json(self):
        """Get the JSON data."""
        json = None
        try:
            async with async_timeout.timeout(10, loop=self.loop):
                response = await self.websession.get(BASE + ",".join(self._symbols))
                json = await response.json()
        except Exception:
            pass

        _LOGGER.debug("Data = %s", json)
        return json

    async def update(self):
        """Update data."""
        try:
            json = await self.get_json()

            if "error" in json:
                raise ValueError(json["error"]["info"])

            result = json["quoteResponse"]["result"]
            data = {}

            for item in result:
                symbol = item["symbol"]
                data[symbol] = {
                    "regularMarketPrice": item["regularMarketPrice"],
                    "shortName": item["shortName"],
                    "fiftyDayAverage": item["fiftyDayAverage"],
                    "regularMarketPreviousClose": item["regularMarketPreviousClose"],
                }
                _LOGGER.debug(
                    "Updated %s=%s", symbol, data[symbol]["regularMarketPrice"],
                )

            self.data = data
            _LOGGER.info("Data updated")
        except ValueError as err:
            _LOGGER.error("Data update error: %s", err.args)
            self.data = None
