# Summary

A custom component to display stock information from [Yahoo finance](https://finance.yahoo.com/).

Currency details can be presented in an different currency than what is reported (`target_currency`). Data is downloaded at regular intervals (`scan_interval`) but a retry is attempted after 20 seconds in case of failure.

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

The above configuration will generate an entity with the id `sensor.yahoofinance_istnx` and current value as the state along with these attributes:

```
attribution: Data provided by Yahoo Finance
currencySymbol: $
symbol: ISTNX
quoteType: MUTUALFUND
quoteSourceName: Delayed Quote
marketState: CLOSED
averageDailyVolume10Day: 0
averageDailyVolume3Month: 0
regularMarketChange: 0.26
regularMarketChangePercent: 0.23
regularMarketDayHigh: 0
regularMarketDayLow: 0
regularMarketPreviousClose: 12.63
regularMarketPrice: 12.89
regularMarketVolume: 0
regularMarketTime: 1618617625
dividendDate: 2021-11-11
fiftyDayAverage: 107.54
fiftyDayAverageChange: 5.35
fiftyDayAverageChangePercent: 0.05
preMarketChange: 0
preMarketChangePercent: 0
preMarketTime: 0
preMarketPrice: 0
postMarketChange: 0
postMarketChangePercent: 0
postMarketPrice: 0
postMarketTime: 0
twoHundredDayAverage: 14.69
twoHundredDayAverageChange: 8.2
twoHundredDayAverageChangePercent: 0.08
fiftyTwoWeekLow: 125
fiftyTwoWeekLowChange: 20.37
fiftyTwoWeekLowChangePercent: 16.29
fiftyTwoWeekHigh: 153.1
fiftyTwoWeekHighChange: -7.74
fiftyTwoWeekHighChangePercent: -5.05
trending: up
unit_of_measurement: USD
friendly_name: Ivy Science & Technology Fund C
icon: mdi:trending-up
```

The `dividendDate` is in ISO format (YYYY-MM-DD) and can be `null`.

## Optional Configuration

### Integration

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

- The fifty_day, post, pre and two_hundred attributes can be suppressed as following. They are included by default.
  ```yaml
  include_fifty_day_values: false
  include_fifty_two_week_values: false
  include_post_values: false
  include_pre_values: false
  include_two_hundred_day_values: false
  ```

### Symbol

- An alternate target currency can be specified for a symbol using the extended declaration format. Here, the symbol EMIM.L is reported in USD but will be presented in EUR. The conversion would be based on the value of the symbol USDEUR=X.

  ```yaml
  symbols:
    - symbol: EMIM.L
      target_currency: EUR
  ```

  If data for the target currency is not found, then the display will remain in original currency. The conversion is only applied on the attributes representing prices.

- The data fetch interval can be fine tuned at symbol level. By default, the `scan_interval` from the integration is used. The minimum value is still 30 seconds. Symbols with the same `scan_interval` are grouped together and loaded through one data coordinator.

  If conversion data needs to be loaded, then that too will get added to the same coordinator. However, if conversion symbol is found in another coordinator, then that will get used.

  ```yaml
  scan_interval:
    hours: 4
  ```

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
- The trending icons themselves cannot be colored but colors can be added using [lovelace-card-mod](https://github.com/thomasloven/lovelace-card-mod). Here [auto-entities](https://github.com/thomasloven/lovelace-auto-entities) is being used to simplify the code.

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

- As of version [1.1.0](https://github.com/iprak/yahoofinance/releases/), the entity id has changed from `yahoofinance.symbol` to `sensor.yahoofinance_symbol`.
- As of version 1.0.0, all the configuration is now under `yahoofinance`. If you are upgrading from an older version, then you would need to adjust the configuration.
- As of version 1.0.1, the minimum `scan_interval` is 30 seconds.
