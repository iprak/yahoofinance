# Summary
A custom component to get stock updates from Yahoo finance.

# Installation

This can be installed by copying all the files from `custom_components/yahoofinance/` to `<config directory>/custom_components/yahoofinance/`.

Next you would define the symbols to be tracked in `configuration.yaml`

Example:

```yaml
sensor:
  - platform: yahoofinance
    symbols:
      - ISTNX

```

The above configuration will generate an entity with the id `yahoofinance.istnx` and current value as the state along with these attributes:

```
attribution: Data provided by Yahoo Finance
currencySymbol: $
fiftyDayAverage: ...
fiftyDayAverageChange: ...
fiftyDayAverageChangePercent: ...
previousClose: ...
marketChange: ...
marketChangePercent: ...
symbol: ISTNX
unit_of_measurement: USD
friendly_name: Ivy Science & Technology Fund C
icon: mdi:currency-usd
```

## Optional settings
* Data fetch interval can be adjusted by specifying the `scan_interval` setting whose default value is 6 hours.
  ```yaml
  scan_interval:
      hours: 4
  ```
* Trending icons (trending-up, trending-down or trending-neutral) can be displayed instead of currency based icon by specifying `show_trending_icon`.
  ```yaml
    show_trending_icon: true
  ```


The component also exposes the service `yahoofinance.refresh_symbols` which will refresh all the data.