"""
The Yahoo finance component.

https://github.com/iprak/yahoofinance
"""

from datetime import timedelta
import logging

import async_timeout
from homeassistant.core import callback
from homeassistant.helpers import event
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util.dt import utcnow

from .const import (
    BASE,
    DATA_REGULAR_MARKET_PRICE,
    NUMERIC_DATA_GROUPS,
    STRING_DATA_KEYS,
)

_LOGGER = logging.getLogger(__name__)
WEBSESSION_TIMEOUT = 15
DELAY_ASYNC_REQUEST_REFRESH = 5
FAILURE_ASYNC_REQUEST_REFRESH = 20


class YahooSymbolUpdateCoordinator(DataUpdateCoordinator):
    """Yahoo finance data update coordinator."""

    @staticmethod
    def parse_symbol_data(symbol_data):
        """Return data pieces which we care about, use 0 for missing numeric values."""
        data = {}

        # get() ensures that we have an entry in symbol_data.
        for group in NUMERIC_DATA_GROUPS:
            for value in NUMERIC_DATA_GROUPS[group]:
                key = value[0]
                data[key] = symbol_data.get(key, 0)

        for key in STRING_DATA_KEYS:
            data[key] = symbol_data.get(key)

        return data

    def __init__(self, symbols, hass, update_interval) -> None:
        """Initialize."""
        self._symbols = symbols
        self.data = None
        self.loop = hass.loop
        self.websession = async_get_clientsession(hass)
        self._update_interval = update_interval
        self._failure_update_interval = timedelta(seconds=FAILURE_ASYNC_REQUEST_REFRESH)

        super().__init__(
            hass,
            _LOGGER,
            name="YahooSymbolUpdateCoordinator",
            update_method=self._async_update,
            update_interval=update_interval,
        )

    def get_next_update_interval(self):
        """Get the update interval for the next async_track_point_in_utc_time call."""
        if self.last_update_success:
            return self._update_interval
        else:
            _LOGGER.warning(
                "Error obtaining data, retrying in %d seconds.",
                FAILURE_ASYNC_REQUEST_REFRESH,
            )
            return self._failure_update_interval

    @callback
    def _schedule_refresh(self) -> None:
        """Schedule a refresh."""
        if self._unsub_refresh:
            self._unsub_refresh()
            self._unsub_refresh = None

        # We _floor_ utcnow to create a schedule on a rounded second,
        # minimizing the time between the point and the real activation.
        # That way we obtain a constant update frequency,
        # as long as the update process takes less than a second

        update_interval = self.get_next_update_interval()
        if update_interval is not None:
            self._unsub_refresh = async_track_point_in_utc_time(
                self.hass,
                self._handle_refresh_interval,
                utcnow().replace(microsecond=0) + update_interval,
            )

    def get_symbols(self):
        """Return symbols tracked by the coordinator."""
        return self._symbols

    async def _async_request_refresh_later(self, _now):
        """Request async_request_refresh."""
        await self.async_request_refresh()

    def add_symbol(self, symbol) -> bool:
        """Add symbol to the symbol list."""
        if symbol not in self._symbols:
            self._symbols.append(symbol)

            # Request a refresh to get data for the missing symbol.
            # This would have been called while data for sensor was being parsed.
            # async_request_refresh has debouncing built into it, so multiple calls
            # to add_symbol will still resut in single refresh.
            event.async_call_later(
                self.hass,
                DELAY_ASYNC_REQUEST_REFRESH,
                self._async_request_refresh_later,
            )

            _LOGGER.info(
                "Added %s and requested update in %d seconds.",
                symbol,
                DELAY_ASYNC_REQUEST_REFRESH,
            )
            return True

        return False

    async def get_json(self):
        """Get the JSON data."""
        json = None
        url = BASE + ",".join(self._symbols)
        _LOGGER.debug("Requesting data from '%s'", url)

        async with async_timeout.timeout(WEBSESSION_TIMEOUT, loop=self.loop):
            response = await self.websession.get(url)
            json = await response.json()

        _LOGGER.debug("Data = %s", json)
        return json

    async def _async_update(self):
        """
        Return updated data if new JSON is valid.

        The exception will get properly handled in the caller (DataUpdateCoordinator.async_refresh)
        which also updates last_update_success. UpdateFailed is raised if JSON is invalid.
        """

        json = await self.get_json()

        if json is None:
            raise UpdateFailed("No data received")

        if "quoteResponse" not in json:
            raise UpdateFailed("Data invalid, 'quoteResponse' not found.")

        quoteResponse = json["quoteResponse"]  # pylint: disable=invalid-name

        if "error" in quoteResponse:
            if quoteResponse["error"] is not None:
                raise UpdateFailed(quoteResponse["error"])

        if "result" not in quoteResponse:
            raise UpdateFailed("Data invalid, no 'result' found")

        result = quoteResponse["result"]
        if result is None:
            raise UpdateFailed("Data invalid, 'result' is None")

        # Using current data if available. If returned data is missing some symbols then we might be
        # able to use previous data.
        data = self.data or {}

        pos = 0
        symbols_count = len(self._symbols)

        # We should receive data matching the symbols requested

        for symbol_data in result:
            symbol_received = symbol_data["symbol"]
            symbol_requested = None

            if pos < symbols_count:
                symbol_requested = self._symbols[pos]
                pos += 1

                if symbol_requested != symbol_received:
                    _LOGGER.warning(
                        "Requested data for %s and received %s",
                        symbol_requested,
                        symbol_received,
                    )

            # Sometimes data for USDEUR=X just contains EUR=X, giving preference to the requested
            # symbol instead of symbol from data.
            symbol = symbol_requested or symbol_received

            data[symbol] = self.parse_symbol_data(symbol_data)

            _LOGGER.debug(
                "Updated %s to %s",
                symbol,
                data[symbol][DATA_REGULAR_MARKET_PRICE],
            )

        _LOGGER.info("All symbols updated")
        return data
