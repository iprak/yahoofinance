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
symbol: XYZ
averageDailyVolume10Day: 16
averageDailyVolume3Month: 1745
fiftyDayAverage: 284.3
fiftyDayAverageChange: -17.09
fiftyDayAverageChangePercent: -0.0
postMarketChange: -0.02999878
postMarketChangePercent: -0.1
postMarketPrice: 267.
regularMarketChange: 0.339
regularMarketChangePercent: 0.127
regularMarketDayHigh: 27
regularMarketDayLow: 26
regularMarketPreviousClose: 26
regularMarketPrice: 267.25
regularMarketVolume: 14
twoHundredDayAverage: 261.
twoHundredDayAverageChange: 6.0
twoHundredDayAverageChangePercent: 0.02
unit_of_measurement: USD
friendly_name: ...
icon: 'mdi:trending-up'
```

## Optional settings

- Data fetch interval can be adjusted by specifying the `scan_interval` setting whose default value is 6 hours.
  ```yaml
  scan_interval:
    hours: 4
  ```
- Trending icons (trending-up, trending-down or trending-neutral) can be displayed instead of currency based icon by specifying `show_trending_icon`.
  ```yaml
  show_trending_icon: true
  ```

The component also exposes the service `yahoofinance.refresh_symbols` which will refresh all the data.
