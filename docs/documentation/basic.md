
# Basic Functions

Lets explore various functions of NSEPython -

## Logger Function <Badge text="Recommended" />

We use [Python Logging Function](https://docs.python.org/3/howto/logging.html). So You can use it to debug your code. Lets add one line to our previous code and enable the logger function and see the output -

**Input**

```py
from nsepython import *
logging.basicConfig(level=logging.DEBUG)

def nse_custom_function_secfno(symbol,attribute="lastPrice"):
    positions = nsefetch('https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O')
    endp = len(positions['data'])
    for x in range(0, endp):
        if(positions['data'][x]['symbol']==symbol.upper()):
            return positions['data'][x][attribute]

print(nse_custom_function_secfno("Reliance"))
print(nse_custom_function_secfno("Reliance","pChange"))
```

**Output**

```sh
DEBUG:urllib3.connectionpool:Starting new HTTPS connection (1): www.nseindia.com:443
DEBUG:urllib3.connectionpool:https://www.nseindia.com:443 "GET /api/equity-stockIndices?index=SECURITIES%20IN%20F%26O HTTP/1.1" 401 272
DEBUG:urllib3.connectionpool:Starting new HTTP connection (1): nseindia.com:80
DEBUG:urllib3.connectionpool:http://nseindia.com:80 "GET / HTTP/1.1" 301 0
DEBUG:urllib3.connectionpool:Starting new HTTP connection (1): www.nseindia.com:80
DEBUG:urllib3.connectionpool:http://www.nseindia.com:80 "GET / HTTP/1.1" 301 0
DEBUG:urllib3.connectionpool:Starting new HTTPS connection (1): www.nseindia.com:443
DEBUG:urllib3.connectionpool:https://www.nseindia.com:443 "GET / HTTP/1.1" 200 40642
DEBUG:urllib3.connectionpool:https://www.nseindia.com:443 "GET /api/equity-stockIndices?index=SECURITIES%20IN%20F%26O HTTP/1.1" 200 24124
2094.45
DEBUG:urllib3.connectionpool:Starting new HTTPS connection (1): www.nseindia.com:443
DEBUG:urllib3.connectionpool:https://www.nseindia.com:443 "GET /api/equity-stockIndices?index=SECURITIES%20IN%20F%26O HTTP/1.1" 200 24124
5.99
```

## Getting the FNO List

**Input**

```py
print(fnolist())
```

**Output**
```sh
['BANKNIFTY', 'NIFTY', 'FINNIFTY', 'ADANIENT', 'ADANIPOWER', 'AMARAJABAT', 'ACC', 'PVR', 'RAMCOCEM', 'AMBUJACEM', 'APOLLOHOSP', 'ASIANPAINT', 'AUROPHARMA', 'AXISBANK', 'BAJAJ-AUTO', 'BAJAJFINSV', 'BAJFINANCE', 'ADANIPORTS', 'BALKRISIND', 'BHARTIARTL', 'BANDHANBNK', 'BATAINDIA', 'BEL', 'BERGEPAINT', 'BHARATFORG', 'BHEL', 'BOSCHLTD', 'BRITANNIA', 'CANBK', 'CIPLA', 'COALINDIA', 'COLPAL', 'CUMMINSIND', 'DABUR', 'BANKBARODA', 'DIVISLAB', 'DRREDDY', 'EICHERMOT', 'EXIDEIND', 'FEDERALBNK', 'GAIL', 'GLENMARK', 'GRASIM', 'HAVELLS', 'HCLTECH', 'HDFCLIFE', 'HEROMOTOCO', 'HINDALCO', 'HINDPETRO', 'HINDUNILVR', 'ICICIBANK', 'ICICIPRULI', 'INDIGO', 'INDUSINDBK', 'INFY', 'ITC', 'JUBLFOOD', 'JUSTDIAL', 'KOTAKBANK', 'LICHSGFIN', 'LUPIN', 'MANAPPURAM', 'MARICO', 'MARUTI', 'BIOCON', 'CADILAHC', 'MCDOWELL-N', 'MFSL', 'MGL', 'MINDTREE', 'MOTHERSUMI', 'MRF', 'MUTHOOTFIN', 'NATIONALUM', 'NCC', 'NIITTECH', 'NMDC', 'NTPC', 'PEL', 'PETRONET', 'PFC', 'PIDILITIND', 'RBLBANK', 'RECLTD', 'SAIL', 'SBIN', 'SIEMENS', 'SRF', 'SRTRANSFIN', 'SUNTV', 'TATAPOWER', 'TECHM', 'TITAN', 'TORNTPHARM', 'TORNTPOWER', 'TVSMOTOR', 'UJJIVAN', 'ULTRACEMCO', 'UPL', 'VOLTAS', 'ASHOKLEY', 'CONCOR', 'INFRATEL', 'BPCL', 'CHOLAFIN', 'DLF', 'EQUITAS', 'ESCORTS', 'IDEA', 'JSWSTEEL', 'LT', 'GODREJCP', 'GODREJPROP', 'SBILIFE', 'HDFC', 'HDFCBANK', 'IDFCFIRSTB', 'JINDALSTEL', 'M&M', 'M&MFIN', 'UBL', 'NAUKRI', 'NESTLEIND', 'ONGC', 'PAGEIND', 'POWERGRID', 'RELIANCE', 'SHREECEM', 'SUNPHARMA', 'TATAMOTORS', 'TATASTEEL', 'CENTURYTEX', 'VEDL', 'APOLLOTYRE', 'PNB', 'TATACHEM', 'IGL', 'IOC', 'TATACONSUM', 'TCS', 'WIPRO', 'ZEEL', 'L&TFH', 'IBULHSGFIN', 'GMRINFRA']
```

It will give you the entire list of FNO.

## Running Status

This is basically a dumb function but quite handy. You can understand it from the source code -

```py
def running_status():
    start_now=datetime.datetime.now().replace(hour=9, minute=15, second=0, microsecond=0)
    end_now=datetime.datetime.now().replace(hour=15, minute=30, second=0, microsecond=0)
    return start_now<datetime.datetime.now()<end_now
```

**Input**

```py
print(running_status())
```

**Output**
```sh
False
```

It will give `True` if the market is running and `False` if the market is not running.

## Getting Option Chain Data

This is a straight JSON Data output directly from the NSE.

**Input**

```py
print(nse_optionchain_scrapper('PVR'))
```

**Output**
The Output will show a huge JSON data which will may the loadtime of this site sensitive.

[Click Here to see it](/nsepython/files/file2.json)

You can check the section of [Parsing the Data with Pandas in the nsefetch() function](nsefetch.html#parsing-the-data-with-pandas) for reference.

You can also alternatively use `option_chain()` function instead of `nse_optionchain_scrapper()`.

## OI Chain Builder Function

### Usage
```py
oi_data,ltp,crontime=oi_chain_builder(symbol,expiry,oi_mode,mode)
```

### Inputs
- symbol = FNO Symbol
- expiry(Optional) = "latest" (By default) or, You can choose next expiry by typing the expiry dates like "30-Jul-2020"
- oi_mode(Optional) = "full" (By default) or "compact" (It will fetch all options info).

### Output
- oi_data = It will be a Pandas Dataframe.
- ltp = LTP of the symbol
- crontime = Data’s Updation Time as per NSE Server when fetched

### Example

**Input**

```py
oi_data, ltp, crontime = oi_chain_builder("RELIANCE","latest","full")
print(oi_data)
print(ltp)
print(crontime)
```

**Output**
```sh
CALLS_Chart  CALLS_OI  ...  PUTS_OI  PUTS_Chart
0           0.0       4.0  ...      4.0         0.0
1           0.0       0.0  ...      0.0         0.0
2           0.0       0.0  ...     98.0         0.0
3           0.0       0.0  ...      0.0         0.0
4           0.0       0.0  ...      0.0         0.0
..          ...       ...  ...      ...         ...
62          0.0     395.0  ...      0.0         0.0
63          0.0       0.0  ...      0.0         0.0
64          0.0       0.0  ...      0.0         0.0
65          0.0       0.0  ...      0.0         0.0
66          0.0     172.0  ...      8.0         0.0

[67 rows x 23 columns]
2094.45
28-May-2021 15:30:00
```

## Getting live Quotes API

There are two types of APIs that fetch live quotes for stock in NSE.

- [nseindia.com/api/quote-equity?symbol=BAJAJFINSV](https://nseindia.com/api/quote-equity?symbol=BAJAJFINSV)
- [nseindia.com/api/quote-derivative?symbol=BANKNIFTY](https://nseindia.com/api/quote-derivative?symbol=BANKNIFTY)

Equity API and Derivatives API will show a huge JSON data which will may the loadtime of this site sensitive.

You can check the section of [Parsing the Data with Pandas in the nsefetch() function](nsefetch.html#parsing-the-data-with-pandas) for reference.

```py
print(nse_eq("JUSTDIAL"))
print(nse_fno("BANKNIFTY"))
```

- You can also alternatively use `quote_equity()` function instead of `nse_eq()`.
- You can also alternatively use `quote_derivative()` function instead of `nse_fno()`.

Note -
- `nse_eq()` and `quote_equity()` will paste the output from the Equity API.
- `quote_derivative()` and `nse_fno()` will paste the output from Derivatives API.

## Stocks API

To get LTP of any stock, You need to do this -
```py
print(nse_eq("JUSTDIAL")['priceInfo']['lastPrice'])
```

For Open, High, Low, Clsoe, You need to do this -
```py
print(nse_eq("JUSTDIAL")['priceInfo']['open'])`
print(nse_eq("JUSTDIAL")['priceInfo']['intraDayHighLow']['min'])
print(nse_eq("JUSTDIAL")['priceInfo']['intraDayHighLow']['max'])
print(nse_eq("JUSTDIAL")['priceInfo']['close'])
```

You can also find things like sector's PE or sector's name of which the stock belong -
```py
print(nse_eq("JUSTDIAL")['metadata']['pdSectorPe'])
print(nse_eq("JUSTDIAL")['metadata']['pdSectorInd'])
```
## Derivatives API

To get LTP of any derivative's underlying, You need to do this -
```py
print(nse_fno("BANKNIFTY")['underlyingValue'])
```

These APIs show a very detailed level of data. You need to explore yourself using the JSON formats. If there is any significant stuff, I may create a separate functions for it later on.

## Quote API

If We see the source code -
```py
def nse_quote(symbol):
    symbol = nsesymbolpurify(symbol)

    if any(x in symbol for x in fnolist()):
        payload = nsefetch('https://www.nseindia.com/api/quote-derivative?symbol='+symbol)
    else:
        payload = nsefetch('https://www.nseindia.com/api/quote-equity?symbol='+symbol)
    return payload
```
It actually checks if it is index or non-index and acts as a universal function towards the quote system defined using `nse_eq()` and `nse_fno()`. It will automatically give the correct scrip info.

## Quote LTP API
```py
print(nse_quote_ltp("BANKNIFTY"))
```
It will print the price of the BankNIFTY Index.

```py
print(nse_quote_ltp("BANKNIFTY","latest","Fut"))
```
It will print the price of BankNIFTY Futures of the current expiry.

```py
print(nse_quote_ltp("RELIANCE","latest","Fut"))
```
It will print the price of Reliance Futures of the current expiry.

```py
print(nse_quote_ltp("RELIANCE"))
```
It will print the price of Reliance.

```py
print(nse_quote_ltp("BANKNIFTY","13-Aug-2020","PE",21000))
print(nse_quote_ltp("RELIANCE","latest","PE",2300))
```
You can also use it in this way to find the option prices of a particular strike price of particular expiry.

::: tip
- These APIs show a very detailed level of data.
- You need to explore yourself using the JSON formats.
- If there is any significant stuff, I may create a separate functions for it later on.
:::

## Expiry List Function

In case You want to get all the expiry dates of a stock which has derivatives.

**Input**
```py
print(expiry_list('ACC'))
```

**Output**

It will be a Pandas Dataframe.
```py
Date
0  24-Jun-2021
1  29-Jul-2021
```
