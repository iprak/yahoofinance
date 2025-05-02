"""Config flow for file integration."""

from copy import deepcopy
from datetime import timedelta
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import callback

# from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from . import BASIC_SYMBOL_SCHEMA
from .const import (
    CONF_DECIMAL_PLACES,
    CONF_NO_UNIT,
    CONF_SHOW_CURRENCY_SYMBOL_AS_UNIT,
    CONF_SHOW_TRENDING_ICON,
    CONF_SYMBOLS,
    CONF_TARGET_CURRENCY,
    DEFAULT_CONF_DECIMAL_PLACES,
    DEFAULT_CONF_NO_UNIT,
    DEFAULT_CONF_SHOW_CURRENCY_SYMBOL_AS_UNIT,
    DEFAULT_CONF_SHOW_TRENDING_ICON,
    DEFAULT_OPTIONS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MINIMUM_SCAN_INTERVAL,
    VALUES_DEFAULT_MAP,
)
from .data import SymbolData

BOOLEAN_SELECTOR = BooleanSelector()
SYMBOLS_SELECTOR = TextSelector(TextSelectorConfig(multiple=True))
SCAN_INTERVAL_SELECTOR = NumberSelector(
    NumberSelectorConfig(
        min=MINIMUM_SCAN_INTERVAL.seconds,
        mode=NumberSelectorMode.BOX,
    )
)


OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_SCAN_INTERVAL,
            # default=options.get(CONF_SCAN_INTERVAL)
            DEFAULT_SCAN_INTERVAL.total_seconds(),
        ): vol.All(vol.Coerce(int), vol.Clamp(min=MINIMUM_SCAN_INTERVAL.seconds)),
        vol.Optional(
            CONF_TARGET_CURRENCY,
            # default=options.get(CONF_TARGET_CURRENCY),
        ): TextSelector(),
        vol.Optional(
            CONF_SHOW_TRENDING_ICON,
            # default=options.get(CONF_SHOW_TRENDING_ICON)
            DEFAULT_CONF_SHOW_TRENDING_ICON,
        ): BOOLEAN_SELECTOR,
        vol.Optional(
            CONF_SHOW_CURRENCY_SYMBOL_AS_UNIT,
            # default=options.get(CONF_SHOW_CURRENCY_SYMBOL_AS_UNIT)
            DEFAULT_CONF_SHOW_CURRENCY_SYMBOL_AS_UNIT,
        ): BOOLEAN_SELECTOR,
        vol.Optional(
            CONF_DECIMAL_PLACES,
            # default=options.get(CONF_DECIMAL_PLACES) or DEFAULT_CONF_DECIMAL_PLACES,
        ): NumberSelector(
            NumberSelectorConfig(
                min=0,
                step=DEFAULT_CONF_DECIMAL_PLACES,
                mode=NumberSelectorMode.BOX,
            )
        ),
    }
)


# CONFIG_SCHEMA: vol.Schema = vol.Schema(
#     {vol.Required(CONF_SYMBOLS): SYMBOLS_SELECTOR}
# ).extend(OPTIONS_SCHEMA.schema)


class YahooFinanceOptionsFlowHandler(OptionsFlow):
    """Handle Yahoo Finance options."""

    _current_symbol: SymbolData
    _global_options: dict[str, Any] | None

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Init object."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""

        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "symbol_options",
                "global_options",
                "edit_symbol_list",
            ],
        )

    async def async_step_symbol_options(
        self, user_input: dict[str, Any] | None = None, errors=None
    ) -> ConfigFlowResult:
        """Mange symbol options."""
        return await self.async_step_pick_symbol_for_update(user_input)

    async def async_step_pick_symbol_for_update(
        self, user_input: dict[str, Any] | None = None, errors=None
    ) -> ConfigFlowResult:
        """Mange symbol options."""

        if user_input is not None:
            self._current_symbol = user_input.get("SYMBOL")
            return await self.async_step_update_symbol_options()

        symbols = self.config_entry.options.get(CONF_SYMBOLS)
        schema = vol.Schema(
            {
                vol.Required("SYMBOL"): SelectSelector(
                    SelectSelectorConfig(options=symbols)
                )
            }
        )
        return self.async_show_form(
            step_id="pick_symbol_for_update",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_update_symbol_options(
        self, user_input: dict[str, Any] | None = None, errors=None
    ) -> ConfigFlowResult:
        """Mange symbol options."""

        if user_input is not None:
            return self.async_abort(reason="already_configured")

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_TARGET_CURRENCY,
                    # default=self._current_symbol.target_currency
                ): BASIC_SYMBOL_SCHEMA,
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    # default=self._current_symbol.scan_interval
                ): SCAN_INTERVAL_SELECTOR,
                vol.Optional(
                    CONF_NO_UNIT,
                    #                    default=self._current_symbol.no_unit or DEFAULT_CONF_NO_UNIT,
                ): BOOLEAN_SELECTOR,
            }
        )

        return self.async_show_form(
            step_id="update_symbol_options",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_global_options(
        self, user_input: dict[str, Any] | None = None, errors=None
    ) -> ConfigFlowResult:
        """Mange symbols options."""

        if user_input is not None:
            self._global_options = user_input
            return await self.async_step_global_attributes()

        return self.async_show_form(
            step_id="global_options",
            data_schema=self._get_options_schema(),
            errors=errors,
        )

    async def async_step_global_attributes(
        self, user_input: dict[str, Any] | None = None, errors=None
    ) -> ConfigFlowResult:
        """Mange symbols attributes."""

        if user_input is not None:
            symbols = {CONF_SYMBOLS: self.config_entry.options.get(CONF_SYMBOLS)}
            new_data = {**symbols, **self._global_options, **user_input}
            self.hass.config_entries.async_update_entry(
                self._config_entry,
                options=new_data,
            )
            # await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_abort(reason="already_configured")
            # return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="global_attributes",
            data_schema=self._get_attributes_schema(),
            errors=errors,
        )

    def _get_attributes_schema(self) -> vol.Schema:
        """Get schema of symbol attributes."""

        options = self.config_entry.options
        schema_data = {}

        for entry in VALUES_DEFAULT_MAP.items():
            schema_data[
                vol.Optional(
                    entry[0],
                    default=options.get(entry[0]) or entry[1],
                )
            ] = BOOLEAN_SELECTOR

        return self.add_suggested_values_to_schema(
            vol.Schema(schema_data), self.config_entry.options
        )

    def _get_options_schema(self) -> vol.Schema:
        """Get schema of symbol options."""
        schema = vol.Schema(
            {
                vol.Optional(CONF_SCAN_INTERVAL): SCAN_INTERVAL_SELECTOR,
                vol.Optional(CONF_TARGET_CURRENCY): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.TEXT)
                ),
                vol.Optional(CONF_SHOW_TRENDING_ICON): BOOLEAN_SELECTOR,
                vol.Optional(CONF_SHOW_CURRENCY_SYMBOL_AS_UNIT): BOOLEAN_SELECTOR,
                vol.Optional(CONF_DECIMAL_PLACES): NumberSelector(
                    NumberSelectorConfig(
                        min=0,
                        step=DEFAULT_CONF_DECIMAL_PLACES,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
            }
        )

        return self.add_suggested_values_to_schema(schema, self.config_entry.options)

    async def async_step_edit_symbol_list(
        self, user_input: dict[str, Any] | None = None, errors=None
    ) -> ConfigFlowResult:
        """Mange editing symbols list."""
        errors: dict[str, str] = {}
        options = self.config_entry.options

        if user_input is not None:
            symbols = _validate_symbols(user_input.get(CONF_SYMBOLS), errors)

            if symbols:
                # data = self.config_entry.data
                new_data = deepcopy(dict(options))
                if CONF_SYMBOLS in new_data:
                    new_data.pop(CONF_SYMBOLS)
                new_data[CONF_SYMBOLS] = symbols

                return self.async_create_entry(title="Yahoo Finance", data=new_data)

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_SYMBOLS,
                ): SYMBOLS_SELECTOR
            }
        )

        return self.async_show_form(
            step_id="edit_symbol_list",
            data_schema=self.add_suggested_values_to_schema(data_schema, options),
            errors=errors,
        )

    async def async_step_edit_options(
        self, user_input: dict[str, Any] | None = None, errors=None
    ) -> ConfigFlowResult:
        """Mange options for the integration."""

        errors = errors or {}

        if user_input is not None:
            options = deepcopy(dict(self.config_entry.options))
            new_data = {**options, **{k: v for k, v in user_input.items() if v}}

            return self.async_create_entry(
                title="Yahoo Finance",
                data=new_data,
            )

        return self.async_show_form(
            step_id="edit_options",
            data_schema=self.add_suggested_values_to_schema(
                self._extra_attributes_schema().extend(self._values_options_schema()),
                self.config_entry.options,
            ),
            errors=errors,
        )


class YahooFinanceConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Yahoo Finance."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}
        self._options: dict[str, Any] = deepcopy(DEFAULT_OPTIONS)
        # deepcopy(DEFAULT_OPTIONS)
        # self._conn_string: bool | None = None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> YahooFinanceOptionsFlowHandler:
        """Get the options flow for this handler."""
        return YahooFinanceOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initiated by the user."""

        errors: dict[str, str] = {}
        # description_placeholders: dict[str, str] = {}

        if user_input is not None:
            symbols = _validate_symbols(user_input.get(CONF_SYMBOLS), errors)

            if symbols:
                return self.async_create_entry(
                    title="Yahoo Finance",
                    data={},
                    options={CONF_SYMBOLS: symbols},
                )

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_SYMBOLS, default=(user_input or {}).get(CONF_SYMBOLS)
                ): SYMBOLS_SELECTOR
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def async_step_update_symbols(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initiated by the user."""
        return True

    async def async_step_update_options(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initiated by the user."""
        return True

    async def async_step_import(
        self, import_data: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Import config from configuration.yaml."""
        assert import_data is not None
        # self._async_abort_entries_match(import_data)
        return await self.async_step_add_sensor(user_input=import_data, yaml=True)

        # for key in DEFAULT_OPTIONS:
        #     if key in import_data:
        #         self._options[key] = import_data.pop(key)

        # if CONF_SCAN_INTERVAL in import_data:
        #     scan_interval: timedelta = import_data.pop(CONF_SCAN_INTERVAL)
        #     self._options[CONF_SCAN_INTERVAL] = scan_interval.seconds

        # symbol_definitions: list[SymbolDefinition] = None

        # if CONF_SYMBOLS in import_data:
        #     symbol_definitions = import_data.pop(CONF_SYMBOLS)

        #     for value in symbol_definitions:
        #         scan_interval = value.get(CONF_SCAN_INTERVAL)
        #         if scan_interval:
        #             scan_interval = scan_interval.seconds

        # # errors = await validate_data(self._data)
        # return self.async_create_entry(
        #     title="Yahoo Finance",
        #     data=symbol_definitions,
        #     options=self._options,
        # )


def _validate_symbols(symbols: list[str], errors: dict[str, str]) -> list[str]:
    """Validate input symbols."""
    parsed_symbols: set = None

    if symbols:
        parsed_symbols = {(item.strip().upper()) for item in symbols if item}

    if parsed_symbols:
        parsed_symbols = list(parsed_symbols)
        for item in parsed_symbols:
            if not _is_single_word(item):
                errors["base"] = "invalid_symbol"
                return None

        return parsed_symbols

    errors["base"] = "invalid_symbol"
    return None


def _is_single_word(text: str):
    """Check if the text is a single word."""
    return " " not in text
