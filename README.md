# Summary

A custom component to display stock information from Yahoo finance.

# Installation

This can be installed through [HACS](https://hacs.xyz/) or by copying all the files from `custom_components/yahoofinance/` to `<config directory>/custom_components/yahoofinance/`.

# Configuration

Define the symbols to be tracked and optional parameters in `configuration.yaml`.

```yaml
# Example configuration.yaml entry
yahoofinance:
  symbols:
    - ISTNX
```

The above configuration will generate an entity with the id `yahoofinance.istnx` and current value as the state along with these attributes:

```
attribution: Data provided by Yahoo Finance
currencySymbol: $
symbol: ISTNX
quoteType: MUTUALFUND
quoteSourceName: Delayed Quote
averageDailyVolume10Day: 16
averageDailyVolume3Month: 1745
fiftyDayAverage: 284.3
fiftyDayAverageChange: -17.09
fiftyDayAverageChangePercent: -0.0
postMarketChange: -0.03
postMarketChangePercent: -0.1
postMarketPrice: 267.
regularMarketChange: 0.34
regularMarketChangePercent: 0.13
regularMarketDayHigh: 27
regularMarketDayLow: 26
regularMarketPreviousClose: 26
regularMarketPrice: 267.25
regularMarketVolume: 14
twoHundredDayAverage: 261.2
twoHundredDayAverageChange: 6.0
twoHundredDayAverageChangePercent: 0.02
trending: up
unit_of_measurement: USD
friendly_name: ...
icon: 'mdi:trending-up'
```

## Optional Configuration

- Data fetch interval can be adjusted by specifying the `scan_interval` setting whose default value is 6 hours and the minimum value is 30 seconds.
  ```yaml
  scan_interval:
    hours: 4
  ```
  You can disable automatic update by passing `None` for `scan_interval`.

- Trending icons (trending-up, trending-down or trending-neutral) can be displayed instead of currency based icon by specifying `show_trending_icon`.
  ```yaml
  show_trending_icon: true
  ```
- All numeric values are by default rounded to 2 places of decimal. This can be adjusted by the `decimal_places` setting. A value of 0 will return in integer values and -1 will suppress rounding.
  ```yaml
  decimal_places: 3
  ```
- An alternate target currency can be specified for a symbol using the extended declaration format. Here, the symbol EMIM.L is reported in USD but will be presented in EUR. The conversion would be based on the value of the symbol USDEUR=X.

  ```yaml
  symbols:
    - symbol: EMIM.L
      target_currency: EUR
    ```

  If data for the target currency is not found, then the display will remain in original currency. The conversion is only applied on the attributes representing prices.


## Examples
- The symbol can also represent a financial index such as [this](https://finance.yahoo.com/world-indices/).

  ```yaml
  symbols:
    - ^SSMI
  ```
- Yahoo also provides currency conversion as a symbol.
  ```yaml
  symbols:
    - GBPUSD=X
  ```
- The trending icons themselves cannot be colored but colors can be added using [browser_mod](https://github.com/thomasloven/hass-browser_mod/). Here [auto-entities](https://github.com/thomasloven/lovelace-auto-entities) is being used to simplify the code.

  ```yaml
  - type: custom:auto-entities
    card:
      type: entities
      title: Financial
    filter:
      include:
        - group: group.stocks
          options:
            entity: this.entity_id
            style: |
              :host {
                --paper-item-icon-color: {% set value=state_attr(config.entity,"trending") %}
                                        {% if value=="up" -%} green
                                        {% elif value=="down" -%} red
                                        {% else %} var(--paper-item-icon-color))
                                        {% endif %};
  ```

# Services

The component exposes the service `yahoofinance.refresh_symbols` which can be used to refresh all the data.


# Breaking Changes

- As of version 1.0.0, all the configuration is now under `yahoofinance`. If you are upgrading from an older version, then you would need to adjust the configuration.
- As of version 1.0.1, the minimum `scan_interval` is 30 seconds.