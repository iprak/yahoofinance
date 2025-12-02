![GitHub Release](https://img.shields.io/github/v/release/iprak/yahoofinance)
[![License](https://img.shields.io/packagist/l/phplicengine/bitly)](https://packagist.org/packages/phplicengine/bitly)
<a href="https://buymeacoffee.com/leolite1q" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" height="20px"></a>

## Summary

A custom component to display stock information from [Yahoo finance](https://finance.yahoo.com/).

Currency details can be presented in an different currency than what is reported (`target_currency`). Data is downloaded at regular intervals (`scan_interval`) but a retry is attempted after 20 seconds in case of failure.

Note: ```This integration will mostly only work in US mainland. Data privacy requirements like GDPR can cause requests to fail. This is as of release 1.2.12.```

## Installation

This can be installed through [HACS](https://hacs.xyz/) or by copying all the files from `custom_components/yahoofinance/` to `<config directory>/custom_components/yahoofinance/`.

## Configuration

Define the symbols to be tracked and optional parameters in `configuration.yaml`.

```yaml
# Example configuration.yaml entry
yahoofinance:
  symbols:
    - ISTNX
```

The above configuration will generate an entity with the id `sensor.yahoofinance_istnx` and current value as the state along with these attributes:

```
state_class: measurement
attribution: Data provided by Yahoo Finance
currencySymbol: $
symbol: ISTNX
quoteType: MUTUALFUND
quoteSourceName: Delayed Quote
marketState: PRE
averageDailyVolume10Day: 0
averageDailyVolume3Month: 0
regularMarketChange: -0.5
regularMarketChangePercent: -0.57
regularMarketDayHigh: 0
regularMarketDayLow: 0
regularMarketPreviousClose: 88.34
regularMarketPrice: 87.84
regularMarketVolume: 0
regularMarketTime: 2025-08-16T00:01:15+00:00
forwardPE: 0
trailingPE: 0
fiftyDayAverage: 83.88
fiftyDayAverageChange: 3.96
fiftyDayAverageChangePercent: 4.73
preMarketChange: 0
preMarketChangePercent: 0
preMarketTime: 0
preMarketPrice: 0
postMarketChange: 0
postMarketChangePercent: 0
postMarketPrice: 0
postMarketTime: 0
twoHundredDayAverage: 75.97
twoHundredDayAverageChange: 11.87
twoHundredDayAverageChangePercent: 15.63
fiftyTwoWeekLow: 57.36
fiftyTwoWeekLowChange: 30.48
fiftyTwoWeekLowChangePercent: 53.14
fiftyTwoWeekHigh: 88.41
fiftyTwoWeekHighChange: -0.57
fiftyTwoWeekHighChangePercent: -0.64
dividendDate: null
dividendRate: 0
dividendYield: 0
trailingAnnualDividendRate: 0
trailingAnnualDividendYield: 0
trending: down
unit_of_measurement: $
icon: mdi:trending-down
friendly_name: Delaware Ivy Science and Techno
```

#### Attributes
* The attributes can be null if there is no data present.
* The `dividendDate` is in ISO format (YYYY-MM-DD).



## Optional Configuration

### Integration

- Data fetch interval can be adjusted by specifying the `scan_interval` setting whose default value is 6 hours and the minimum value is 30 seconds.

  ```yaml
  scan_interval:
    hours: 4
  ```

  You can disable automatic update by passing `manual` for `scan_interval`.

- Trending icons (trending-up, trending-down or trending-neutral) can be displayed instead of currency based icon by specifying `show_trending_icon`.
  ```yaml
  show_trending_icon: true
  ```
- All numeric values are by default rounded to 2 places of decimal. This can be adjusted by the `decimal_places` setting. A value of 0 will return in integer values and -1 will suppress rounding.

  ```yaml
  decimal_places: 3
  ```

- The dividend, fifty_day, post, pre and two_hundred attributes can be included as following. They are all excluded by default.
  ```yaml
  include_dividend_values: true
  include_fifty_day_values: true
  include_fifty_two_week_values: true
  include_post_values: true
  include_pre_values: true
  include_two_hundred_day_values: true
  ```

- Show post, pre market prices in the default sensor value, by default disabled. When enabled, it is recommended to also set `include_post_values` and `include_pre_values` to `true`.
  ```yaml
  include_post_values: true
  include_pre_values: true
  show_off_market_values: true
  ```

  ### Optional attributes
  #### include_dividend_values
  - dividendDate
  - dividendRate
  - dividendYield
  - trailingAnnualDividendRate
  - trailingAnnualDividendYield

  #### include_fifty_day_values
  - fiftyDayAverage
  - fiftyDayAverageChange
  - fiftyDayAverageChangePercent

  #### include_pre_values
  - preMarketChange
  - preMarketChangePercent
  - preMarketPrice
  - preMarketTime

  #### include_post_values
  - postMarketChange
  - postMarketChangePercent
  - postMarketPrice
  - postMarketTime

  #### include_fifty_two_week_values
  - fiftyTwoWeekLow
  - fiftyTwoWeekLowChange
  - fiftyTwoWeekLowChangePercent
  - fiftyTwoWeekHigh
  - fiftyTwoWeekHighChange
  - fiftyTwoWeekHighChangePercent

  ### include_two_hundred_day_values
  - twoHundredDayAverage
  - twoHundredDayAverageChange
  - twoHundredDayAverageChangePercent

- The currency symbol e.g. $ can be show as the unit instead of USD by setting `show_currency_symbol_as_unit: true`.
  - **Note:** Using this setting will generate a warning like `The unit of this entity changed to '$' which can't be converted ...` You will have to manually resolve it by picking the first option to update the unit of the historicalvalues without convertion. This can be done from `Developer tools > STATISTICS`.


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

  ```yaml
  scan_interval:
    minutes: 5
  ```

  ```yaml
  scan_interval: 300
  ```

- The `unit_of_measurement` can be suppressed by setting `no_unit: true`. This could be used for index symbols if no currency unit is desired to be displayed.

  ```yaml
    - symbol: BND
      no_unit: true
  ```
  - **Note:** Using this setting will generate a warning like `The unit of sensor.yahoofinance_gspc cannot be converted to the unit of previously compiled statistics (USD). Generation of long term statistics will be suppressed unless the unit changes back to USD or a compatible unit.` You will have to manually resolve it as mentioned in the message otherwise new data might not show in cards.

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

- A complete sample

```
yahoofinance:
  include_post_values: false
  include_pre_values: false
  show_trending_icon: true
  decimal_places: 2
  scan_interval:
    hours: 4
  symbols:
    - USDINR=X
    - UNP
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

## Services

* The integration configuration can be reloaded from the `YAHOO FINANCE` option on `YAML` tab in `Developer tools`.

* The component exposes the service `yahoofinance.refresh_symbols` which can be used to refresh all the data.

## Events

* The event `yahoofinance_data_updated` is sent when data is updated. It contains the list of symbols updated. This can be used to take actions upon data update.


## Breaking Changes
- 1.5.0 - All dividend values are controlled by the new setting `include_dividend_values`. The fifty_day, post, pre, two_hundred and dividend attributes are now `excluded` by default.
- As of version [1.2.5](https://github.com/iprak/yahoofinance/releases/), `scan_interval` can be `manual` to suppress automatic update.

- As of version [1.1.0](https://github.com/iprak/yahoofinance/releases/), the entity id has changed from `yahoofinance.symbol` to `sensor.yahoofinance_symbol`.
- As of version 1.0.0, all the configuration is now under `yahoofinance`. If you are upgrading from an older version, then you would need to adjust the configuration.
- As of version 1.0.1, the minimum `scan_interval` is 30 seconds.
