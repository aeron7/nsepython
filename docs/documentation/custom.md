# Custom Functions

[Unofficed](https://www.unofficed.com) is a community. So, there are lots of custom functions made to the needs of different requests and to simplify our needs.

Although some may sound silly, it is no harm to have them in arsenal. Most of them are developed on the top of the previous functions.


## Illiquid Options Bid Ask

`nse_optionchain_ltp() Function` is the best function. Let's have a look at the source code. It actually gives you bid/ask. Lifesaver if you end up in illiquid options.

```py
def nse_optionchain_ltp(payload,strikePrice,optionType,inp=0,intent=""):
    expiryDate=payload['records']['expiryDates'][inp]
    for x in range(len(payload['records']['data'])):
      if((payload['records']['data'][x]['strikePrice']==strikePrice) & (payload['records']['data'][x]['expiryDate']==expiryDate)):
          if(intent==""): return payload['records']['data'][x][optionType]['lastPrice']
          if(intent=="sell"): return payload['records']['data'][x][optionType]['bidprice']
          if(intent=="buy"): return payload['records']['data'][x][optionType]['askPrice']
```

Originally created for [Artemis](https://unofficed.com/artemis/).

Here is the usage:
```py
payload=nse_optionchain_scrapper('BANKNIFTY')
print(nse_optionchain_ltp(payload,23000,"CE",0,"sell"))
```

The variable `inp` is used in many places in this documentation. So, Let's highlight it.

## INP Variable

inp -

* inp = 0 means current expiry. It is the default.
* inp = 1 means next expiry and so on.

intent -

* If you write your intent as a sell. It will take the bid price.
* If you write your intent as a buy. It will take the ask price.

LTP is quite deceptive when you trade using ITM right?

## PCR API

Here is the usage:

```py
payload=nse_optionchain_scrapper('BANKNIFTY')
print(pcr(payload,1))
```

As `inp` is 1 here, It will show PCR of next expiry!

## Expiry Details API

Originally created for [Artemis](https://unofficed.com/artemis/), it shows the date of the expiry and number of days to expiry **(DTE)**

```py
nse_expirydetails(payload,inp)
```
- `payload` is JSON input.
- `inp` (Optional) - It tells which expiry. 0 being the current. 1 being the next. Default is 0.

**Usage:**
```py
payload=nse_optionchain_scrapper('BANKNIFTY')
currentExpiry,dte=nse_expirydetails(payload,1)
print(currentExpiry)
print(dte)
```
**Output:**
```py
2021-06-10
11
```

As `inp` is 1 here, It is showing the details of Expiry and PCR of next expiry!

## SecFNO Scarapper Function

This function is written as a complex usage of `nsefetch()` function.

You can check the section of [Building Custom functions with nsefetch() function](nsefetch.html#building-custom-functions) for usage.
