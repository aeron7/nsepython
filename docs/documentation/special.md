# Special Functions

These are very unusual function which are first time having python wrapper on them.

## The Results API

nseindia.com/companies-listing/corporate-filings-financial-results

The API looks like this -

[nseindia.com/api/corporates-financial-results?index=equities&period=Quarterly](https://nseindia.com/api/corporates-financial-results?index=equities&period=Quarterly)

`index` has three types:

* equities
* debt
* sme

`period` has four types:

* Quarterly
* Annual
* Half-Yearly
* Others

**Usage:**

```py
nse_results(index,period)
```

Default Value of index is `equities` and period is `Quarterly` in nse_results() function.

**Example Usage:**

```py
nse_results()
nse_results("equities","Others")
```

## The Holiday API

There are two types -
- [https://www.nseindia.com/api/?type=trading](https://www.nseindia.com/api/?type=trading)
- [https://www.nseindia.com/api/?type=clearing](https://www.nseindia.com/api/?type=clearing)

Here is how to use the function

```py
nse_holidays(type)
```
or,
```py
holiday_master(type)
```

type = `trading` or `clearing`. By default, `trading` will be selected.

Here is how to see the holidays of FNOs -

```py
print(pd.json_normalize(nse_holidays()['FO']))
```

## The Event Calendar API

[nseindia.com/companies-listing/corporate-filings-event-calendar](https://nseindia.com/companies-listing/corporate-filings-event-calendar)

API Link: [https://www.nseindia.com/api/event-calendar](https://www.nseindia.com/api/event-calendar)

**Example Usage:**

```py
nse_events()
```

::: tip
You can do a cross search between FNO companies and the companies listed here.
:::

## The Past Results API

[nseindia.com/companies-listing/corporate-filings-financial-results-comparision](https://nseindia.com/companies-listing/corporate-filings-financial-results-comparision)

API Link: [nseindia.com/api/results-comparision?symbol=JUSTDIAL](https://nseindia.com/api/results-comparision?symbol=JUSTDIAL)

**Example Usage:**

```py
print(nse_past_results('JUSTDIAL'))
```

## The Block Deals API

[https://www.nseindia.com/market-data/block-deal-watch](https://www.nseindia.com/market-data/block-deal-watch)

API Link: [https://nseindia.com/api/block-deal](https://nseindia.com/api/block-deal)

**Example Usage:**

```py
print(nse_blockdeal())
```

## The Market Status API

Although We have a function that merely checks if we are in market time but this API Endpoint comes from NSE.

API Link: [https://nseindia.com/api/marketStatus](https://nseindia.com/api/marketStatus)

**Example Usage:**

```py
print(nse_marketStatus())
```

## The NSE Circular API

There are two APIs that fetch NSE Circular. One that truncates to the latest data and another that shows all the circulars.

**Example Usage:**

```py
print(nse_circular("latest"))
```

This will show the NSE's latest circulars.

API Link: [https://www.nseindia.com/api/latest-circular](https://www.nseindia.com/api/latest-circular)

```py
print(nse_circular("all"))
```

This will show the NSE's all circulars.

API Link: [https://www.nseindia.com/api/circulars](https://www.nseindia.com/api/circulars)

## The FII/DII API

It fetches data of FII/DII in both `Pandas` and raw mode. By "raw", it means You get the usual `List` format.

[https://www.nseindia.com/reports/fii-dii](https://www.nseindia.com/reports/fii-dii)

**Example Usage:**

```py
print(nse_fiidii())
```

**Output:**

```py
category         date buyValue sellValue netValue
0     DII **  28-May-2021  6440.88   5165.66  1275.22
1  FII/FPI *  28-May-2021  5917.71   5004.12   913.59
```

If You want the output in `List` mode directly. Use -

```py
print(nse_fiidii("list"))
```

**Output:**

```py
[{'category': 'DII **', 'date': '28-May-2021', 'buyValue': '6440.88', 'sellValue': '5165.66', 'netValue': '1275.22'}, {'category': 'FII/FPI *', 'date': '28-May-2021', 'buyValue': '5917.71', 'sellValue': '5004.12', 'netValue': '913.59'}]
```
In case Pandas throws error, It will come as output default.
