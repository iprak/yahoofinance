"""The Yahoo finance component.

https://github.com/iprak/yahoofinance
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
from http import HTTPStatus
from http.cookies import SimpleCookie
import logging
import re
from typing import Any, Final

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers import event
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    BASE,
    CONSENT_HOST,
    CRUMB_RETRY_DELAY,
    CRUMB_RETRY_DELAY_429,
    DATA_REGULAR_MARKET_PRICE,
    GET_CRUMB_URL,
    INITIAL_REQUEST_HEADERS,
    INITIAL_URL,
    MANUAL_SCAN_INTERVAL,
    NUMERIC_DATA_DEFAULTS,
    NUMERIC_DATA_GROUPS,
    REQUEST_HEADERS,
    STRING_DATA_KEYS,
)

_LOGGER = logging.getLogger(__name__)
REQUEST_TIMEOUT: Final = 10
DELAY_ASYNC_REQUEST_REFRESH: Final = 5
FAILURE_ASYNC_REQUEST_REFRESH: Final = 20


class CrumbCoordinator:
    """Class to gather crumb/cookie details."""

    _instance = None
    """Static instance of CrumbCoordinator."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize."""

        self.cookies: SimpleCookie[str] = None
        """Cookies for requests."""
        self.crumb: str | None = None
        """Crumb for requests."""
        self._hass = hass

        self.retry_duration = CRUMB_RETRY_DELAY
        """Crumb retry request delay."""

    @staticmethod
    def get_static_instance(hass: HomeAssistant) -> CrumbCoordinator:
        """Return the static CrumbCoordinator instance."""
        if CrumbCoordinator._instance is None:
            CrumbCoordinator._instance = CrumbCoordinator(hass)
        return CrumbCoordinator._instance

    def reset(self) -> None:
        """Reset crumb and cookies."""
        self.crumb = self.cookies = None

    async def try_get_crumb_cookies(self) -> str | None:
        """Try to get crumb and cookies for data requests."""

        consent_data = await self.initial_navigation(INITIAL_URL)
        if consent_data is None:  # Consent check failed
            return None

        if consent_data.need_consent:
            if not await self.process_consent(consent_data):
                return None

            data = await self.initial_navigation(consent_data.successful_consent_url)

            if data is None:  # Something went bad, we did get consent
                _LOGGER.error("Post consent navigation failed")
                return None

            if data.need_consent:
                _LOGGER.error(
                    "Yahoo reported needing consent even after we got it once"
                )
                return None

        if self.cookies_missing():
            _LOGGER.error("Attempting to get crumb but have no cookies")

        await self.try_crumb_page()
        return self.crumb

    async def initial_navigation(self, url: str) -> ConsentData | None:
        """Navigate to base page. This determines if consent is needed.

        Returns:
            None if consent check failed or the consent response

        """

        websession = async_get_clientsession(self._hass)
        _LOGGER.debug("Navigating to base page %s", url)

        try:
            async with websession.get(
                url,
                headers=INITIAL_REQUEST_HEADERS,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as response:
                _LOGGER.debug("Response %d, URL: %s", response.status, response.url)

                if response.status != HTTPStatus.OK:
                    _LOGGER.error(
                        "Failed to navigate to %s, status=%d, reason=%s",
                        url,
                        response.status,
                        response.reason,
                    )
                    return None

                # This request will return cookies only if consent is not needed
                if response.cookies:
                    self.cookies = response.cookies

                # https://guce.yahoo.com/consent?brandType=nonEu&gcrumb=eZ_Jbm0&done=https%3A%2F%2Ffinance.yahoo.com%2F
                if response.url.host.lower() == CONSENT_HOST:
                    _LOGGER.info("Consent page %s detected", response.url)

                    return ConsentData(
                        need_consent=True,
                        consent_content=await response.text(),
                        consent_post_url=response.url,
                    )

                _LOGGER.debug("No consent needed, have cookies=%s", bool(self.cookies))

        except TimeoutError as ex:
            _LOGGER.error("Timed out accessing initial url. %s", ex)
        except aiohttp.ClientError as ex:
            _LOGGER.error("Error accessing initial url. %s", ex)

        return ConsentData()

    async def process_consent(self, consent_data: ConsentData) -> bool:
        """Process GDPR consent."""

        websession = async_get_clientsession(self._hass)
        form_data = self.build_consent_form_data(consent_data.consent_content)
        _LOGGER.debug("Posting consent %s", str(form_data))

        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                response = await websession.post(
                    consent_data.consent_post_url,
                    data=form_data,
                    headers=INITIAL_REQUEST_HEADERS,
                )

                # Sample responses
                # 302 https://guce.yahoo.com/copyConsent?sessionId=3_cc-session_0d6c4281-76f7-44ce-8783-6db9d4f39c40&lang=nb-NO
                # 302 https://finance.yahoo.com/?guccounter=1
                # 200

                if response.status != HTTPStatus.OK:
                    _LOGGER.error(
                        "Failed to post consent %d, reason=%s",
                        response.status,
                        response.reason,
                    )
                    return False

                if response.cookies:
                    self.cookies = response.cookies

                consent_data.successful_consent_url = response.url

                _LOGGER.debug(
                    "After consent processing, have cookies=%s", bool(self.cookies)
                )
                return True

        except TimeoutError as ex:
            _LOGGER.error("Timed out processing consent. %s", ex)
        except aiohttp.ClientError as ex:
            _LOGGER.error("Error accessing consent url. %s", ex)

        return False

    def cookies_missing(self) -> bool:
        """Check if we don't have any cookies."""
        return self.cookies is None or len(self.cookies) == 0

    async def try_crumb_page(self) -> str | None:
        """Try to get crumb from the end point."""

        _LOGGER.info("Accessing crumb page")
        websession = async_get_clientsession(self._hass)

        async with websession.get(
            GET_CRUMB_URL,
            headers=REQUEST_HEADERS,
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            cookies=self.cookies,
        ) as response:
            _LOGGER.debug("Crumb response status: %d, %s", response.status, response)

            if response.status == HTTPStatus.OK:
                self.crumb = await response.text()
                if not self.crumb:
                    _LOGGER.error("No crumb reported")

                _LOGGER.debug("Crumb page reported %s", self.crumb)
                return self.crumb

            _LOGGER.error(
                "Crumb request responded with status=%d, reason=%s",
                response.status,
                response.reason,
            )

            if response.status == 429:
                # Ideally we would want to use the seconds passed back in the header
                # for 429 but there seems to be no such value.
                self.retry_duration = CRUMB_RETRY_DELAY_429
            else:
                self.retry_duration = CRUMB_RETRY_DELAY

            return None

    # async def parse_crumb_from_content(self, content: str) -> str:
    #     """Parse and update crumb from response content."""

    #     _LOGGER.debug("Parsing crumb from content (length: %d)", len(content))

    #     start_pos = content.find('"crumb":"')
    #     _LOGGER.debug("Start position: %d", start_pos)
    #     end_pos = -1

    #     if start_pos != -1:
    #         start_pos = start_pos + 9
    #         end_pos = content.find('"', start_pos + 10)
    #         _LOGGER.debug("End position: %d", end_pos)
    #         if end_pos != -1:
    #             self.crumb = (
    #                 content[start_pos:end_pos]
    #                 .encode()
    #                 .decode("unicode_escape")
    #             )

    #     # Crumb was not located
    #     if not self.crumb:
    #         _LOGGER.info(
    #             "Crumb not found, start position: %d, ending position: %d. Refer to YahooFinanceCrumbContent.log in the config folder.",
    #             start_pos,
    #             end_pos,
    #         )

    #         if _LOGGER.isEnabledFor(logging.INFO):
    #             await self._hass.async_add_executor_job(
    #                 write_utf8_file,
    #                 self._hass.config.path("YahooFinanceCrumbContent.log"),
    #                 content,
    #             )

    def build_consent_form_data(self, content: str) -> dict[str, str]:
        """Build consent form data from response content."""
        pattern = r'<input.*?type="hidden".*?name="(.*?)".*?value="(.*?)".*?>'
        matches = re.findall(pattern, content)
        basic_data = {"reject": "reject"}
        additional_data = dict(matches)
        return {**basic_data, **additional_data}


class YahooSymbolUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Yahoo finance data update coordinator."""

    @staticmethod
    def parse_symbol_data(symbol_data: dict) -> dict[str, any]:
        """Return data pieces which we care about, use 0 for missing numeric values."""
        data = {}

        # get() ensures that we have an entry in symbol_data.
        for data_group in NUMERIC_DATA_GROUPS.values():
            for value in data_group:
                key = value[0]

                # Default value for most missing numeric keys is 0
                default_value = NUMERIC_DATA_DEFAULTS.get(key, 0)

                data[key] = symbol_data.get(key, default_value)

        for key in STRING_DATA_KEYS:
            data[key] = symbol_data.get(key)

        return data

    @staticmethod
    def fix_conversion_symbol(symbol: str, symbol_data: any) -> str:
        """Fix the conversion symbol from data."""

        if symbol is None or symbol == "" or not symbol.endswith("=X"):
            return symbol

        # Data analysis showed that data for conversion symbol has 'shortName': 'USD/EUR'
        short_name = symbol_data["shortName"] or ""
        from_to = short_name.split("/")
        if len(from_to) != 2:
            return symbol

        from_currency = from_to[0]
        to_currency = from_to[1]
        if from_currency == "" or to_currency == "":
            return symbol

        conversion_symbol = f"{from_currency}{to_currency}=X"

        if conversion_symbol != symbol:
            _LOGGER.info(
                "Conversion symbol updated to %s from %s", conversion_symbol, symbol
            )

        return conversion_symbol

    def __init__(
        self,
        symbols: list[str],
        hass: HomeAssistant,
        update_interval: timedelta,
        cc: CrumbCoordinator,
    ) -> None:
        """Initialize."""
        self._symbols = symbols
        self.data = None
        self.loop = hass.loop
        self.websession = async_get_clientsession(hass)
        self._failure_update_interval = timedelta(seconds=FAILURE_ASYNC_REQUEST_REFRESH)
        self._cc = cc

        if isinstance(update_interval, str) and update_interval == MANUAL_SCAN_INTERVAL:
            update_interval = None

        self._update_interval = update_interval

        super().__init__(
            hass,
            _LOGGER,
            name="YahooSymbolUpdateCoordinator",
            update_interval=update_interval,
        )

    def get_symbols(self) -> list[str]:
        """Return symbols tracked by the coordinator."""
        return self._symbols

    async def _async_request_refresh_later(self, _now):
        """Request async_request_refresh."""
        await self.async_request_refresh()

    def add_symbol(self, symbol: str) -> bool:
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
                "Added %s and requested update in %d seconds",
                symbol,
                DELAY_ASYNC_REQUEST_REFRESH,
            )
            return True

        return False

    async def get_json(self) -> dict:
        """Get the JSON data."""

        url = await self.build_request_url()
        cookies = self._cc.cookies
        _LOGGER.debug("Requesting data from '%s'", url)

        async with asyncio.timeout(REQUEST_TIMEOUT):
            response = await self.websession.get(
                url, headers=REQUEST_HEADERS, cookies=cookies
            )

            result_json = await response.json()

            if response.status == HTTPStatus.OK:
                return result_json

            # Sample errors:
            #   {'finance':{'result': None, 'error': {'code': 'Unauthorized', 'description': 'Invalid Crumb'}}}
            #   {'finance':{'result': None, 'error': {'code': 'Unauthorized', 'description': 'Invalid Cookie'}}}
            finance_error_code_tuple = (
                YahooSymbolUpdateCoordinator.get_finance_error_code(result_json)
            )

            if finance_error_code_tuple:
                (
                    finance_error_code,
                    finance_error_description,
                ) = finance_error_code_tuple

                _LOGGER.error(
                    "Received status %d (%s %s) for %s",
                    response.status,
                    finance_error_code,
                    finance_error_description,
                    url,
                )

                # Reset crumb so that it gets recalculated
                if finance_error_code == "Unauthorized":
                    _LOGGER.log("Resetting crumbs")
                    self._cc.reset()

            else:
                _LOGGER.error(
                    "Received status %d for %s, result=%s",
                    response.status,
                    url,
                    result_json,
                )

        return None

    async def build_request_url(self) -> str:
        """Build the request url."""
        url = BASE + ",".join(self._symbols)

        crumb = self._cc.crumb
        if crumb is None:
            crumb = await self._cc.try_get_crumb_cookies()
        if crumb is not None:
            url = url + "&crumb=" + crumb

        return url

    @staticmethod
    def get_finance_error_code(error_json) -> tuple[str, str] | None:
        """Parse error code from the json."""
        if error_json:
            finance = error_json.get("finance")
            if finance:
                finance_error = finance.get("error")
                if finance_error:
                    return finance_error.get("code"), finance_error.get("description")

        return None

    async def _async_update_data(self) -> dict[str, Any]:
        """Return updated data if new JSON is valid.

        The exception will get properly handled in the caller (DataUpdateCoordinator.async_refresh)
        which also updates last_update_success. UpdateFailed is raised if JSON is invalid.
        """

        # Set update interval for failure and reset it later if everything was okay
        self.update_interval = self._failure_update_interval

        try:
            json = await self.get_json()
        except (TimeoutError, aiohttp.ClientError) as error:
            raise UpdateFailed(error) from error

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

        (error_encountered, data) = self.process_json_result(result)
        self.update_interval = self._update_interval

        if error_encountered:
            _LOGGER.info("Data = %s", result)
        else:
            _LOGGER.debug("Data = %s", result)

        return data

    def process_json_result(self, result) -> tuple[bool, dict[str, Any]]:
        """Process json result and return (error status, updated data)."""

        # Using current data if available. If returned data is missing then we might be
        # able to use previous data.
        data = self.data or {}

        symbols = self._symbols.copy()
        error_encountered = False

        for symbol_data in result:
            symbol = symbol_data["symbol"]

            if symbol in symbols:
                symbols.remove(symbol)
            else:
                # Sometimes data for USDEUR=X just contains EUR=X, try to fix such
                # symbols. The source of truth is the symbol in the data since data
                # pieces could be out of order.
                fixed_symbol = self.fix_conversion_symbol(symbol, symbol_data)

                if fixed_symbol in symbols:
                    symbols.remove(fixed_symbol)
                    symbol = fixed_symbol
                else:
                    _LOGGER.warning("Received %s not in symbol list", symbol)
                    error_encountered = True

            data[symbol] = self.parse_symbol_data(symbol_data)

            _LOGGER.debug(
                "Updated %s to %s",
                symbol,
                data[symbol][DATA_REGULAR_MARKET_PRICE],
            )

        if len(symbols) > 0:
            _LOGGER.warning("No data received for %s", symbols)
            error_encountered = True

        return (error_encountered, data)


@dataclass
class ConsentData:
    """Class for data related to GDPR consent."""

    consent_content: str = ""
    """Consent verification content"""
    consent_post_url: str = ""
    """Url from consent check where data is to be submitted"""
    successful_consent_url: str = ""
    """Url to navigate to after successful consent"""
    need_consent: bool = False
    """Consent is needed"""
