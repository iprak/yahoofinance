# Summary
A custom component to get stock updates from Yahoo finance.

# Installation

This can be installed by copying all the files from `custom_components/yahoofinance/` to `<config directory>/custom_components/yahoofinance/`.

Next you would define the symbols to be tracked in `configuration.yaml`

Example:

```yaml
sensor:
  platform: yahoofinance
  scan_interval:
    hours: 4
  symbols:
    - ISTNX 
  
```

The above configuration will generate an entity with the id `yahoofinance.istnx` and current value as the state along with these attributes:

```
attribution: Data provided by Yahoo Finance
currencySymbol: $
symbol: ISTNX
fiftyDayAverage: ...
previousClose: ...
unit_of_measurement: USD
friendly_name: Ivy Science & Technology Fund C
icon: mdi:currency-usd
```

`scan_interval` is optional and the default value is 6 hours.


The component also exposes the service `yahoofinance.refresh_symbols` which will refresh all the data.