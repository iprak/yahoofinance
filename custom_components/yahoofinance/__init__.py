"""The Yahoo finance component.

https://github.com/iprak/yahoofinance
"""

from __future__ import annotations

from datetime import timedelta

import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_DECIMAL_PLACES,
    CONF_INCLUDE_FIFTY_DAY_VALUES,
    CONF_INCLUDE_FIFTY_TWO_WEEK_VALUES,
    CONF_INCLUDE_POST_VALUES,
    CONF_INCLUDE_PRE_VALUES,
    CONF_INCLUDE_TWO_HUNDRED_DAY_VALUES,
    CONF_NO_UNIT,
    CONF_SHOW_CURRENCY_SYMBOL_AS_UNIT,
    CONF_SHOW_TRENDING_ICON,
    CONF_SYMBOLS,
    CONF_TARGET_CURRENCY,
    DEFAULT_CONF_DECIMAL_PLACES,
    DEFAULT_CONF_INCLUDE_FIFTY_DAY_VALUES,
    DEFAULT_CONF_INCLUDE_FIFTY_TWO_WEEK_VALUES,
    DEFAULT_CONF_INCLUDE_POST_VALUES,
    DEFAULT_CONF_INCLUDE_PRE_VALUES,
    DEFAULT_CONF_INCLUDE_TWO_HUNDRED_DAY_VALUES,
    DEFAULT_CONF_NO_UNIT,
    DEFAULT_CONF_SHOW_CURRENCY_SYMBOL_AS_UNIT,
    DEFAULT_CONF_SHOW_TRENDING_ICON,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
    MANUAL_SCAN_INTERVAL,
    MINIMUM_SCAN_INTERVAL,
    SERVICE_REFRESH,
)
from .coordinator import CrumbCoordinator, YahooSymbolUpdateCoordinator
from .data import SymbolDefinition, YahooFinanceData

BASIC_SYMBOL_SCHEMA = vol.All(cv.string, vol.Upper)

PLATFORMS = [Platform.SENSOR]
type YahooFinanceConfigEntry = ConfigEntry[YahooFinanceData]


def minimum_scan_interval(value: timedelta) -> timedelta:
    """Validate scan_interval is the minimum value."""
    if value < MINIMUM_SCAN_INTERVAL:
        raise vol.Invalid("Scan interval should be at least 30 seconds")
    return value


MANUAL_SCAN_INTERVAL_SCHEMA = vol.All(vol.Lower, MANUAL_SCAN_INTERVAL)
CUSTOM_SCAN_INTERVAL_SCHEMA = vol.All(cv.time_period, minimum_scan_interval)
SCAN_INTERVAL_SCHEMA = vol.Any(MANUAL_SCAN_INTERVAL_SCHEMA, CUSTOM_SCAN_INTERVAL_SCHEMA)

COMPLEX_SYMBOL_SCHEMA = vol.All(
    dict,
    vol.Schema(
        {
            vol.Required("symbol"): BASIC_SYMBOL_SCHEMA,
            vol.Optional(CONF_TARGET_CURRENCY): BASIC_SYMBOL_SCHEMA,
            vol.Optional(CONF_SCAN_INTERVAL): SCAN_INTERVAL_SCHEMA,
            vol.Optional(CONF_NO_UNIT, default=DEFAULT_CONF_NO_UNIT): cv.boolean,
        }
    ),
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_SYMBOLS): vol.All(
                    cv.ensure_list,
                    [vol.Any(BASIC_SYMBOL_SCHEMA, COMPLEX_SYMBOL_SCHEMA)],
                ),
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): SCAN_INTERVAL_SCHEMA,
                vol.Optional(CONF_TARGET_CURRENCY): vol.All(cv.string, vol.Upper),
                vol.Optional(
                    CONF_SHOW_TRENDING_ICON, default=DEFAULT_CONF_SHOW_TRENDING_ICON
                ): cv.boolean,
                vol.Optional(
                    CONF_SHOW_CURRENCY_SYMBOL_AS_UNIT,
                    default=DEFAULT_CONF_SHOW_CURRENCY_SYMBOL_AS_UNIT,
                ): cv.boolean,
                vol.Optional(
                    CONF_DECIMAL_PLACES, default=DEFAULT_CONF_DECIMAL_PLACES
                ): vol.Coerce(int),
                vol.Optional(
                    CONF_INCLUDE_FIFTY_DAY_VALUES,
                    default=DEFAULT_CONF_INCLUDE_FIFTY_DAY_VALUES,
                ): cv.boolean,
                vol.Optional(
                    CONF_INCLUDE_POST_VALUES, default=DEFAULT_CONF_INCLUDE_POST_VALUES
                ): cv.boolean,
                vol.Optional(
                    CONF_INCLUDE_PRE_VALUES, default=DEFAULT_CONF_INCLUDE_PRE_VALUES
                ): cv.boolean,
                vol.Optional(
                    CONF_INCLUDE_TWO_HUNDRED_DAY_VALUES,
                    default=DEFAULT_CONF_INCLUDE_TWO_HUNDRED_DAY_VALUES,
                ): cv.boolean,
                vol.Optional(
                    CONF_INCLUDE_FIFTY_TWO_WEEK_VALUES,
                    default=DEFAULT_CONF_INCLUDE_FIFTY_TWO_WEEK_VALUES,
                ): cv.boolean,
            }
        )
    },
    # The complete HA configuration is passed down to`async_setup`, allow the extra keys.
    extra=vol.ALLOW_EXTRA,
)


def normalize_input_symbols(
    defined_symbols: list, global_scan_interval: timedelta
) -> list[SymbolDefinition]:
    """Normalize input and remove duplicates."""
    symbols = set()
    symbol_definitions: list[SymbolDefinition] = []

    for value in defined_symbols:
        if isinstance(value, str):
            if value not in symbols:
                symbols.add(value)
                symbol_definitions.append(
                    SymbolDefinition(value, scan_interval=global_scan_interval)
                )
        else:
            symbol = value["symbol"]
            if symbol not in symbols:
                symbols.add(symbol)
                symbol_definitions.append(
                    SymbolDefinition(
                        symbol,
                        target_currency=value.get(CONF_TARGET_CURRENCY),
                        scan_interval=value.get(
                            CONF_SCAN_INTERVAL, global_scan_interval
                        ),
                        no_unit=value.get(CONF_NO_UNIT),
                    )
                )

    return symbol_definitions


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the component."""
    # domain_config = config.get(DOMAIN, {})
    # if hass.config_entries.async_entries(DOMAIN):
    #     # We skip import in case we already have config entries
    #     return True

    # # migrate_notify_issue(hass, DOMAIN, "Yahoo", "2024.12.0")
    # hass.async_create_task(
    #     hass.config_entries.flow.async_init(
    #         DOMAIN, context={"source": SOURCE_IMPORT}, data=domain_config
    #     )
    # )
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: YahooFinanceConfigEntry
) -> bool:
    """Set up Yahoo Finance from a config entry."""

    options = dict(entry.options)

    defined_symbols = options.get(CONF_SYMBOLS, [])
    global_scan_interval = options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    symbol_definitions: list[SymbolDefinition]
    symbol_definitions = normalize_input_symbols(defined_symbols, global_scan_interval)
    # domain_config[CONF_SYMBOLS] = symbol_definitions

    # Populate parsed value into domain_config
    # domain_config[CONF_SCAN_INTERVAL] = global_scan_interval

    # Group symbols by scan_interval
    symbols_by_scan_interval: dict[timedelta, list[str]] = {}
    for symbol in symbol_definitions:
        # Use integration level scan_interval if none defined
        if symbol.scan_interval is None:
            symbol.scan_interval = global_scan_interval

        if symbol.scan_interval in symbols_by_scan_interval:
            symbols_by_scan_interval[symbol.scan_interval].append(symbol.symbol)
        else:
            symbols_by_scan_interval[symbol.scan_interval] = [symbol.symbol]

    LOGGER.info("Total %d unique scan intervals", len(symbols_by_scan_interval))

    # Pass down the config to platforms.
    # hass.data[DOMAIN] = {
    #     HASS_DATA_CONFIG: domain_config,
    # }

    async def _setup_coordinator(now=None) -> None:
        # Using a static instance to keep the last successful cookies.
        crumb_coordinator = CrumbCoordinator.get_static_instance(hass)

        crumb = await crumb_coordinator.try_get_crumb_cookies()  # Get crumb first
        if crumb is None:
            delay = crumb_coordinator.retry_duration
            LOGGER.warning("Unable to get crumb, re-trying in %d seconds", delay)
            async_call_later(hass, delay, _setup_coordinator)
            return

        coordinators: dict[timedelta, YahooSymbolUpdateCoordinator] = {}
        for key_scan_interval, symbols in symbols_by_scan_interval.items():
            LOGGER.info(
                "Creating coordinator with scan_interval %s for symbols %s",
                key_scan_interval,
                symbols,
            )
            coordinator = YahooSymbolUpdateCoordinator(
                symbols, hass, key_scan_interval, crumb_coordinator
            )
            coordinators[key_scan_interval] = coordinator

            LOGGER.info(
                "Requesting initial data from coordinator with update interval of %s",
                key_scan_interval,
            )
            await coordinator.async_refresh()

        # Pass down the coordinator to platforms.
        # hass.data[DOMAIN][HASS_DATA_COORDINATORS] = coordinators
        entry.runtime_data = YahooFinanceData(coordinators=coordinators)

        async def handle_refresh_symbols(_call) -> None:
            """Refresh symbol data."""
            LOGGER.info("Processing refresh_symbols")

            for coordinator in coordinators.values():
                await coordinator.async_refresh()

        hass.services.async_register(
            DOMAIN,
            SERVICE_REFRESH,
            handle_refresh_symbols,
        )

        for coordinator in coordinators.values():
            if not coordinator.last_update_success:
                LOGGER.debug(
                    "Coordinator did not report any data, requesting async_refresh"
                )
                hass.async_create_task(coordinator.async_request_refresh())

        # hass.async_create_task(
        #    discovery.async_load_platform(hass, "sensor", DOMAIN, {}, config)
        # )
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        entry.async_on_unload(entry.add_update_listener(update_listener))

    await _setup_coordinator()
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: YahooFinanceConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def update_listener(hass: HomeAssistant, entry: YahooFinanceConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


def convert_to_float(value) -> float | None:
    """Convert specified value to float."""
    try:
        return float(value)
    except:  # noqa: E722 pylint: disable=bare-except
        return None
