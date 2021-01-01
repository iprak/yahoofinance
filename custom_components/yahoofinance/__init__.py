"""
The Yahoo finance component.

https://github.com/iprak/yahoofinance
"""

import asyncio
from datetime import timedelta
import logging

import aiohttp
import async_timeout
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    BASE,
    CONF_DECIMAL_PLACES,
    CONF_SHOW_TRENDING_ICON,
    CONF_SYMBOLS,
    DEFAULT_CONF_SHOW_TRENDING_ICON,
    DEFAULT_DECIMAL_PLACES,
    DOMAIN,
    NUMERIC_DATA_KEYS,
    SERVICE_REFRESH,
    STRING_DATA_KEYS,
)

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(hours=6)
WEBSESSION_TIMEOUT = 10

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_SYMBOLS): vol.All(cv.ensure_list, [cv.string]),
                vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL): cv.time_period,
                vol.Optional(
                    CONF_SHOW_TRENDING_ICON, default=DEFAULT_CONF_SHOW_TRENDING_ICON
                ): cv.boolean,
                vol.Optional(
                    CONF_DECIMAL_PLACES, default=DEFAULT_DECIMAL_PLACES
                ): vol.Coerce(int),
            }
        )
    },
    # The full HA configurations gets passed to `async_setup` so we need to allow
    # extra keys.
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config) -> bool:
    """Set up the Yahoo Finance sensors."""

    domain_config = config[DOMAIN]
    symbols = domain_config.get(CONF_SYMBOLS, [])

    # Make sure all symbols are in upper case
    symbols = [sym.upper() for sym in symbols]
    domain_config[CONF_SYMBOLS] = symbols

    coordinator = YahooSymbolUpdateCoordinator(
        symbols, hass, domain_config.get(CONF_SCAN_INTERVAL)
    )
    await coordinator.async_refresh()

    hass.data[DOMAIN] = {
        "coordinator": coordinator,
        "config": domain_config,
    }

    async def handle_refresh_symbols(_call):
        """Refresh symbol data."""
        _LOGGER.info("Processing refresh_symbols")
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH,
        handle_refresh_symbols,
    )

    hass.async_create_task(async_load_platform(hass, "sensor", DOMAIN, {}, config))
    return True


class YahooSymbolUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage Yahoo finance data update."""

    def __init__(self, symbols, hass, update_interval) -> None:
        """Initialize."""
        self._symbols = symbols
        self.data = None
        self.loop = hass.loop
        self.websession = async_get_clientsession(hass)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self):
        """Fetch the latest data from the source."""
        try:
            await self.update()
        except () as error:
            raise UpdateFailed from error
        return self.data

    async def get_json(self):
        """Get the JSON data."""
        json = None
        try:
            async with async_timeout.timeout(WEBSESSION_TIMEOUT, loop=self.loop):
                response = await self.websession.get(BASE + ",".join(self._symbols))
                json = await response.json()

            _LOGGER.debug("Data = %s", json)
            self.last_update_success = True
        except asyncio.TimeoutError:
            _LOGGER.error("Timed out getting data")
            self.last_update_success = False
        except aiohttp.ClientError as exception:
            _LOGGER.error("Error getting data: %s", exception)
            self.last_update_success = False

        return json

    async def update(self):
        """Update data."""
        json = await self.get_json()
        if json is not None:
            if "error" in json:
                raise ValueError(json["error"]["info"])

            result = json["quoteResponse"]["result"]
            data = {}

            for item in result:
                symbol = item["symbol"]

                # Return data pieces which we care about, use 0 for missing numeric values
                data[symbol] = {}
                for key in NUMERIC_DATA_KEYS:
                    data[symbol][key] = item.get(key, 0)
                for key in STRING_DATA_KEYS:
                    data[symbol][key] = item.get(key)

                _LOGGER.debug(
                    "Updated %s=%s",
                    symbol,
                    data[symbol]["regularMarketPrice"],
                )

            self.data = data
            _LOGGER.info("Data updated")
