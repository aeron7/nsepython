---
pageClass: frontpage-class
---

# nsefetch() Function

Lets explore the most important function of NSEPython -

We added a new function named `nsefetch()` which downloads the NSE website links and parse them into JSONs automatically. If You find any API Endpoint of NSE that has JSON, You can use this function to download bypassing their usual scarping blocks.

Just the put link inside the function! That’s it.

## Basic Usage

**Input**

```py
positions = nsefetch('https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O')
print(positions)
```

**Output**

The Output will show a huge JSON data which will may the loadtime of this site sensitive.

[Click Here to see it](/nsepython/files/file1.json)

## Parsing the Data with Pandas

You can check these following sites to navigate through the data schema or help you to structure bad output of JSON.

- [Best JSON Viewer Online](https://jsonformatter.org/json-viewer)
- [JSON Formatter](https://jsonformatter.curiousconcept.com/) (Preferred)

Let's study how you can manage this huge data by Python and `Pandas` Library.Note that `Pandas` is already preinstalled with `NSEPython`. If You have put the shared JSON Output in the [JSON Formatter](https://jsonformatter.curiousconcept.com/), You will see something like this -

<img :src="$withBase('/images/json1.png')" alt="JSON Formatter">

Anyways, If check it further You can see the `data` holds a `Python List`. All we have to do is to convert the `List` to `Pandas`. [Reference](https://www.geeksforgeeks.org/create-a-pandas-dataframe-from-lists/)

**Input**

```py
from nsepython import *
positions = nsefetch('https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O')
df = pd.DataFrame(positions['data'])
print(df)
```

**Output**

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
155   TVSMOTOR  ...  {'symbol': 'TVSMOTOR', 'companyName': 'TVS Mot..
```

The output is showing `...` as it is too big but anyways, that's the way to parse it. You can add these lines to unlock the full view of Pandas output -

```py
pd.set_option('display.max_columns', None)  # or 1000
pd.set_option('display.max_rows', None)  # or 1000
pd.set_option('display.max_colwidth', -1)  # or 199
pd.options.mode.chained_assignment = None  # default='warn' https://stackoverflow.com/questions/20625582/how-to-deal-with-settingwithcopywarning-in-pandas
```

Alternatively, You can use `for` loop too.

## Building Custom Functions

Let's workout futher on making a custom function using `for` loop to display the LTP and various other attributes of a symbol using this same URL -

**Input**

```py
from nsepython import *

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
2094.45
5.99
```
::: tip
This function also comes by default with `nsepython` installation. Try it out!
:::

So, You can see that the same LTP can be fetched in multiple ways.

You can also design Python beautifully to get other attributes like `pChange` which shows how much percentage it is up or down that day.

The rest of the attributes can be seen from putting the output JSON in the [JSON Formatter](https://jsonformatter.curiousconcept.com/) easily -

<img :src="$withBase('/images/attributes.png')" alt="JSON Formatter">
