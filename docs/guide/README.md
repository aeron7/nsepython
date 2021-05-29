# Welcome

NSEPython is a Python library to get publicly available data on NSE website ie. stock quotes, historical data, live indices, etc.
Thanks for using NSEPython 🙂. Let's get you up and running.

## Installation

To use it, open up your terminal in the desired directory and run the following command:

```sh
pip install nsepython
```

### Notes
- If You’ve other doubts, Ask at [NSEPython Doubts and Discussions](https://forum.unofficed.com/c/programming/nse-python-api/)
- If You’ve feature requests, Ask at [NSEPython Discussion and Feature Request](https://forum.unofficed.com/t/nsepython-discussion-and-feature-request/665)

To upgrade the program to its latest version, run the following command:

```sh
pip install --upgrade nsepython
```

## Getting Started <Badge text="Fast" />
To Initialize, You need to do `from nsepython import *`

**Example**

Fetching the Indices of NSE

**Input**
````py
from nsepython import *   
print(indices)
````

**Output**

````bash
['NIFTY', 'FINNIFTY', 'BANKNIFTY']
````

## Unofficed Session Tutorials <Badge text="Youtube" type="warning"/>

If You have never used Python, Jupyter and are beginner stumbling into this project, Go through this link [Basics of NSEPython Using Python and Jupyter](unofficed.com/quant-session/).

<iframe width="560" height="315" src="https://www.youtube.com/embed/gFvoL1jiq4w" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

## Google Cloud, AWS, Servers <Badge text="Common Problem" type="error"/>

This current version of scrapper does not work with AWS, Google Cloud and web servers. It is not a problem of Python Request. Nse’s robots.txt has blocked all webservers all together. See here [NSE Robots Txt](https://www.nseindia.com/robots.txt).

````md
User-agent: *

Disallow: /static/htmls/
Disallow: /static/src/
Disallow: /server/
Disallow: /api/

Sitemap: https://www.nseindia.com/sitemap.xml
Sitemap: https://www.nseindia.com/sitemap-stocks.xml
````
You can use the curl method and initiate shell commands using Python if you want to do it.

I do not plan to add Curl Method in the library unless I see some other library doing it because - That will increase the load in NSE servers and they will guard up their firewalls causing lots of problems for general scavengers like us like they did with their old website.

::: warning
- If I make NSEPython compatible for servers, it **will not** work in windows laptops.
- If I make NSEPython compatible for laptops, it **will not** work in server.
:::
