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

```py
nse_events()
```

::: tip
You can do a cross search between FNO companies and the companies listed here.
:::

## The Past Results API

[nseindia.com/companies-listing/corporate-filings-financial-results-comparision](https://nseindia.com/companies-listing/corporate-filings-financial-results-comparision)
API Link: [nseindia.com/api/results-comparision?symbol=JUSTDIAL](https://nseindia.com/api/results-comparision?symbol=JUSTDIAL)

Usage:

```py
print(nse_past_results('JUSTDIAL'))
```
