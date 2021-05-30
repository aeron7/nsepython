# NSETools Functions

The Functions are the newest/better adaptaions of the functionality of another wrapper named [NSETools](https://github.com/vsjha18/nsetools) that is depreciated (No longer actively maintained).

## Getting a Stock Quote

NSEPython already has various ways of getting Stock Quotes. However, this function is designed specifically to give output similar/same like NSETools' nse.get_quote() function.

::: warning
It only work for stocks and index that are in derivatives segement.
:::

Before going though other fundamental APIs. We will first see how to get a quote. Assume that we want to fetch current price of Reliance Industries. The only thing we need is NSE Code for this company. The NSE stock code for Infosys is RELIANCE.

**Example Usage:**

```py
print(nsetools_get_quote("reliance"))
```

**Output:**

```json
{
   "symbol":"RELIANCE",
   "identifier":"",
   "series":"EQ",
   "open":"1990",
   "dayHigh":"2105",
   "dayLow":"1990",
   "lastPrice":"2094.45",
   "previousClose":"1976.1",
   "change":118.35,
   "pChange":5.99,
   "totalTradedVolume":26060864,
   "totalTradedValue":53878751450.88,
   "lastUpdateTime":"31-DEC-2999",
   "yearHigh":"2369.35",
   "yearLow":"1412",
   "nearWKH":11.60233819401946,
   "nearWKL":-48.33215297450424,
   "perChange365d":43.05,
   "date365dAgo":"29-May-2020",
   "chart365dPath":"https://static.nseindia.com/sparklines/365d/RELIANCE-EQ.jpg",
   "date30dAgo":"29-Apr-2021",
   "perChange30d":3.5,
   "chart30dPath":"https://static.nseindia.com/sparklines/30d/RELIANCE-EQ.jpg",
   "chartTodayPath":"https://static.nseindia.com/sparklines/today/RELIANCEEQN.jpg",
   "meta":{
      "symbol":"RELIANCE",
      "companyName":"Reliance Industries Limited",
      "industry":"REFINERIES",
      "activeSeries":[
         "EQ"
      ],
      "debtSeries":[

      ],
      "tempSuspendedSeries":[

      ],
      "isFNOSec":true,
      "isCASec":false,
      "isSLBSec":true,
      "isDebtSec":false,
      "isSuspended":false,
      "isETFSec":false,
      "isDelisted":false,
      "isin":"INE002A01018"
   }
}
```

## And the Index Quote

You don’t always need a stock quote. At times it is just enough to know the index status. A market in general is home to many indices, in other words there are more that on index which are traded in a market.

This is true with NSE as well. This is how we will get quote for CNX NIFTY and BANK NIFTY

### The Index API

It will give you output in `Pandas` dataframe.

**Example Usage:**

```py
print(nse_index())
```

**Output:**

```sh
yearLow       last      indexName  ... indexOrder       open indexSubType
0   9,544.35  15,435.65       NIFTY 50  ...       0.00  15,421.20           bm
1  23,907.35  37,394.45  NIFTY NEXT 50  ...       1.00  37,533.00           bm
2  14,123.55  27,122.80       NIFTY IT  ...       2.00  27,238.10           sc
3  19,507.05  35,141.45     NIFTY BANK  ...       3.00  35,345.65           sc
4    14.0525    17.4025      INDIA VIX  ...     4.0000    19.9100           bm
```

The output is truncated because of its massive size. But You can check the name of the columns here by doing -

```py
print(nse_index().columns.values)
```

The output will be -

```py
['yearLow' 'last' 'indexName' 'yearHigh' 'previousClose' 'high'
 'indexType' 'low' 'timeVal' 'percChange' 'indexOrder' 'open'
 'indexSubType']
```

::: tip
So, You can use all of these attributes and play with the Dataframe to make your way out.
:::

### The Index List

Updated version of `get_index_list()` from NSETools.

**Example Usage:**

```py
print(nse_get_index_list())
```

**Output:**

```py
['NIFTY 50', 'NIFTY NEXT 50', 'NIFTY IT', 'NIFTY BANK', 'INDIA VIX', 'NIFTY 100', 'NIFTY 500', 'NIFTY MIDCAP 100', 'NIFTY MIDCAP 50', 'NIFTY INFRA', 'NIFTY REALTY', 'NIFTY50 TR 2X LEV', 'NIFTY CONSUMPTION', 'NIFTY MNC', 'NIFTY PVT BANK', 'NIFTY100 LOWVOL30', 'NIFTY100 QUALTY30', 'NIFTY GS 11 15YR', 'NIFTY PHARMA', 'NIFTY50 PR 1X INV', 'NIFTY COMMODITIES', 'NIFTY GS COMPSITE', 'NIFTY MID LIQ 15', 'NIFTY200MOMENTM30', 'NIFTY CPSE', 'NIFTY FMCG', 'NIFTY GROWSECT 15', 'NIFTY GS 15YRPLUS', 'NIFTY MIDCAP 150', 'NIFTY SERV SECTOR', 'NIFTY100 EQL WGT', 'NIFTY50 PR 2X LEV', 'NIFTY50 VALUE 20', 'NIFTY ALPHA 50', 'NIFTY AUTO', 'NIFTY DIV OPPS 50', 'NIFTY MEDIA', 'NIFTY PSE', 'NIFTY PSU BANK', 'NIFTY50 TR 1X INV', 'NIFTY 200', 'NIFTY ALPHALOWVOL', 'NIFTY ENERGY', 'NIFTY GS 4 8YR', 'NIFTY GS 8 13YR', 'NIFTY MIDSML 400', 'NIFTY100 LIQ 15', 'NIFTY50 EQL WGT', 'NIFTY50 DIV POINT', 'NIFTY200 QUALTY30', 'NIFTY SMLCAP 50', 'NIFTY SMLCAP 100', 'NIFTY METAL', 'NIFTY FIN SERVICE', 'NIFTY SMLCAP 250', 'NIFTY GS 10YR CLN', 'NIFTY100ESGSECLDR', 'NIFTY FINSRV25 50', 'NIFTY GS 10YR', 'NIFTY500 SHARIAH', 'NIFTY50 SHARIAH', 'NIFTY LOW VOLATILITY 50', 'NIFTY HIGH BETA 50', 'NIFTY SHARIAH 25', 'NIFTY MAHINDRA GROUP', 'NIFTY TATA GROUP', 'NIFTY TATA GROUP 25% CAP', 'NIFTY ADITYA BIRLA GROUP', 'NIFTY 50 FUTURES INDEX', 'NIFTY 50 FUTURES TR INDEX', 'NIFTY 50 ARBITRAGE', 'NIFTY QUALITY LOW-VOLATILITY 30', 'NIFTY ALPHA QUALITY LOW-VOLATILITY 30', 'NIFTY ALPHA QUALITY VALUE LOW-VOLATILITY 30', 'NIFTY LARGEMIDCAP 250', 'NIFTY SME EMERGE', 'NIFTY100 ESG', 'NIFTY100 ENHANCED ESG', 'NIFTY500 VALUE 50', 'NIFTY100 ALPHA 30', 'NIFTY MIDCAP150 QUALITY 50', 'NIFTY OIL & GAS', 'NIFTY CONSUMER DURABLES', 'NIFTY HEALTHCARE INDEX', 'NIFTY500 MULTICAP 50:25:25', 'NIFTY50 USD', 'NIFTY 1D RATE INDEX', 'NIFTY 10 YEAR SDL INDEX', 'NIFTY BHARAT BOND INDEX - APRIL 2023', 'NIFTY BHARAT BOND INDEX - APRIL 2030', 'NIFTY BHARAT BOND INDEX - APRIL 2025', 'NIFTY BHARAT BOND INDEX - APRIL 2031']
```

### The Index Quote API

Updated version of `get_index_quote()` from NSETools.

Pick one of the index codes from the above list and use it as follows. For example let’s find index quote for “Nifty Bank”.

**Example Usage:**

```py
print(get_index_quote("nifty bank"))
```

**Output:**

```json
{
   "yearLow":"19,507.05",
   "last":"35,141.45",
   "indexName":"NIFTY BANK",
   "yearHigh":"37,708.75",
   "previousClose":"35,095.05",
   "high":"35,436.65",
   "indexType":"eq",
   "low":"34,977.20",
   "timeVal":"May 28, 2021 15:33:36",
   "percChange":"0.13",
   "indexOrder":"3.00",
   "open":"35,345.65",
   "indexSubType":"sc"
}
```

## Advances Declines

Updated version of `get_advances_declines()` from NSETools.

Advances Declines is a very important feature which, in a brief snapshot, tells you the story of a trading day for the given index.

It containes the number of rising stocks, falling stocks and unchanged stocks in a given trading day, per index.

The following API would return the list of dictionaries containing stats for every index.

**Usage:**

```py
nse_get_advances_declines(mode)
```

`mode` has two values.
- The default value is `pandas`. It will return in Pandas DataFrame.
- Other one is `list`. It will return in List.

If in any case, The Pandas Output ends in error, It will automagically give you output in List.

**Example Usage:**

```py
print(nse_get_advances_declines())
```

**Output:**

```sh
symbol  ...                                               meta
0     RELIANCE  ...  {'symbol': 'RELIANCE', 'companyName': 'Relianc...
1        L&TFH  ...  {'symbol': 'L&TFH', 'companyName': 'L&T Financ...
2        CANBK  ...  {'symbol': 'CANBK', 'companyName': 'Canara Ban...
3      HDFCAMC  ...  {'symbol': 'HDFCAMC', 'companyName': 'HDFC Ass...
4       M&MFIN  ...  {'symbol': 'M&MFIN', 'companyName': 'Mahindra ...
..         ...  ...                                                ...
151        BEL  ...  {'symbol': 'BEL', 'companyName': 'Bharat Elect...
152        UBL  ...  {'symbol': 'UBL', 'companyName': 'United Brewe...
153        MGL  ...  {'symbol': 'MGL', 'companyName': 'Mahanagar Ga...
154  SUNPHARMA  ...  {'symbol': 'SUNPHARMA', 'companyName': 'Sun Ph...
155   TVSMOTOR  ...  {'symbol': 'TVSMOTOR', 'companyName': 'TVS Mot...
```

The output is truncated because of its massive size.


## Top Losers & Gainers

Updated version of `get_top_gainers()` and `get_top_losers()` from NSETools.

The following two APIs provides list of top losing and gaining stocks for the last trading session.

**Example Usage:**

```py
print(nse_get_top_gainers())
```

Similarly, For the Top Losers, the function is -

```py
print(mse_get_top_losers())
```

The output will be on Pandas Dataframe with 5 stocks.

## Getting Lot Sizes

Updated version of `get_fno_lot_sizes()` from NSETools. This is where it gets interesting. Few more functionalities are added here.

### Example 1

```py
print(nse_get_fno_lot_sizes("adaniports"))
```

or,

```py
print(nse_get_fno_lot_sizes("adaniports","list"))
```

**Output:**

```py
1250
```

It will output the lot size of `AdaniPorts` in the current month.

::: danger
This function works perfectly with stocks but can break with indexes because NSE often change their Data Structure.
:::

### Definition

This function works in two methods. One is using `List` and Another one is usuing `Pandas`. You can see the definition here -

```py
def nse_get_fno_lot_sizes(symbol="all",mode="list"):
```

- `Symbol` can be `all` (that's default) or any symbol name.
- `Mode` can be `list` (that's default) or `pandas`.

::: warning
`all`, `list`, `pandas` are case sensitive. The Symbol names are not case sensitive.
:::

Here are example outputs of other variations -

### Example 2

```py
print(nse_get_fno_lot_sizes("adaniports","pandas"))
```

**Output:**

```py
UNDERLYING                            SYMBOL      ...  JUN-25       DEC-25     
5  ADANI PORT & SEZ LTD                  ADANIPORTS  ...                          
```

The output is truncated because of its massive size. It is actually `Pandas` DataFrame with all expiries as it's column name in a sorted manner.

You can follow [this tutorial to work with the Pandas Column Names.](https://www.geeksforgeeks.org/how-to-get-column-names-in-pandas-dataframe/)

### Example 3

```py
print(nse_get_fno_lot_sizes())
```

**Output:**

```py
{'BANKNIFTY': 25, 'FINNIFTY': 40, 'NIFTY': 75, 'AUROPHARMA': 650, 'ADANIPORTS': 1250, 'AARTIIND': 425, 'ALKEM': 200, 'AMARAJABAT': 1000, 'APLLTD': 550, 'APOLLOHOSP': 250, 'APOLLOTYRE': 2500, 'ASHOKLEY': 4500, 'ASIANPAINT': 300, 'AUBANK': 500, 'CADILAHC': 2200, 'AXISBANK': 1200, 'BAJAJ-AUTO': 250, 'BAJAJFINSV': 125, 'BERGEPAINT': 1100, 'BAJFINANCE': 125, 'BALKRISIND': 400, 'BANDHANBNK': 1800, 'BEL': 3800, 'BIOCON': 2300, 'BHARATFORG': 1500, 'BHARTIARTL': 1851, 'BHEL': 10500, 'DEEPAKNTR': 500, 'BRITANNIA': 200, 'CHOLAFIN': 1250, 'COALINDIA': 4200, 'COFORGE': 375, 'DIVISLAB': 200, 'CONCOR': 1563, 'FEDERALBNK': 10000, 'DABUR': 1250, 'HCLTECH': 700, 'DLF': 3300, 'EICHERMOT': 350, 'ESCORTS': 550, 'EXIDEIND': 3600, 'GAIL': 6100, 'GLENMARK': 1150, 'GODREJCP': 1000, 'GODREJPROP': 650, 'GRANULES': 1550, 'GRASIM': 475, 'GUJGASLTD': 1250, 'M&MFIN': 4000, 'HAVELLS': 500, 'HDFC': 300, 'HDFCAMC': 200, 'HDFCBANK': 550, 'HINDALCO': 2150, 'HINDPETRO': 2700, 'HINDUNILVR': 300, 'IBULHSGFIN': 3100, 'ICICIBANK': 1375, 'ICICIGI': 425, 'IDFCFIRSTB': 9500, 'INDIGO': 500, 'IRCTC': 325, 'ITC': 3200, 'JINDALSTEL': 2500, 'SAIL': 9500, 'JSWSTEEL': 1350, 'JUBLFOOD': 250, 'KOTAKBANK': 400, 'LALPATHLAB': 250, 'LICHSGFIN': 2000, 'LT': 575, 'LTI': 150, 'LTTS': 200, 'SUNTV': 1500, 'LUPIN': 850, 'M&M': 700, 'MANAPPURAM': 6000, 'WIPRO': 1600, 'MCDOWELL-N': 1250, 'MFSL': 650, 'MINDTREE': 400, 'MOTHERSUMI': 3500, 'MPHASIS': 325, 'MUTHOOTFIN': 750, 'NAM-INDIA': 1600, 'NATIONALUM': 17000, 'NAUKRI': 125, 'NESTLEIND': 50, 'ADANIENT': 1000, 'NMDC': 6700, 'NTPC': 5700, 'PAGEIND': 30, 'PETRONET': 3000, 'PFC': 6200, 'PFIZER': 125, 'PIDILITIND': 500, 'PIIND': 250, 'POWERGRID': 4000, 'PVR': 407, 'RAMCOCEM': 850, 'RECLTD': 6000, 'SBILIFE': 750, 'SHREECEM': 25, 'SRTRANSFIN': 400, 'SUNPHARMA': 1400, 'TATACHEM': 1000, 'TATACONSUM': 1350, 'TATAMOTORS': 2850, 'CUB': 3100, 'TATAPOWER': 6750, 'TATASTEEL': 850, 'ICICIPRULI': 1500, 'TECHM': 600, 'TITAN': 375, 'TORNTPHARM': 250, 'TORNTPOWER': 1500, 'TVSMOTOR': 1400, 'UBL': 700, 'MARICO': 2000, 'CIPLA': 650, 'UPL': 1300, 'VOLTAS': 500, 'ZEEL': 3000, 'ACC': 500, 'NAVINFLUOR': 225, 'SRF': 125, 'AMBUJACEM': 3000, 'BOSCHLTD': 50, 'INFY': 600, 'L&TFH': 8924, 'BANKBARODA': 11700, 'BATAINDIA': 550, 'BPCL': 1800, 'ONGC': 7700, 'COLPAL': 350, 'VEDL': 3100, 'CUMMINSIND': 600, 'DRREDDY': 125, 'HDFCLIFE': 1100, 'IGL': 1375, 'INDUSTOWER': 2800, 'IOC': 6500, 'MARUTI': 100, 'TRENT': 725, 'MGL': 600, 'MRF': 10, 'PEL': 275, 'RELIANCE': 250, 'SBIN': 1500, 'SIEMENS': 275, 'TCS': 300, 'ULTRACEMCO': 100, 'CANBK': 5400, 'HEROMOTOCO': 300, 'PNB': 16000, 'GMRINFRA': 22500, 'IDEA': 70000, 'INDUSINDBK': 900, 'RBLBANK': 2900}
```

This gives all the lotsize of current month's symbols in a Python List.

### Example 4

```py
print(nse_get_fno_lot_sizes("all","pandas"))
```

**Output:**

```py
UNDERLYING                            SYMBOL      ...  JUN-25       DEC-25     
0    NIFTY BANK                            BANKNIFTY   ...                          
1    NIFTY FINANCIAL SERVICES              FINNIFTY    ...                          
2    NIFTY 50                              NIFTY       ...  75           75         
3    Derivatives on Individual Securities  Symbol      ...                          
4    AUROBINDO PHARMA LTD                  AUROPHARMA  ...                          
..                                    ...         ...  ...          ...          ...
155  PUNJAB NATIONAL BANK                  PNB         ...                          
156  GMR INFRASTRUCTURE LTD.               GMRINFRA    ...                          
157  VODAFONE IDEA LIMITED                 IDEA        ...                          
158  INDUSIND BANK LIMITED                 INDUSINDBK  ...                          
159  RBL BANK LIMITED                      RBLBANK     ...                          

```

The output is truncated because of its massive size. It is actually `Pandas` DataFrame with all expiries as it's column name in a sorted manner.
