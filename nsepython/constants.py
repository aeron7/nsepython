HEADERS: dict[str, str] = {
    "Connection": "keep-alive",
    "Cache-Control": "max-age=0",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.79 Safari/537.36",
    "Sec-Fetch-User": "?1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-Mode": "navigate",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
}

CURL_HEADERS: str = """ -H "authority: beta.nseindia.com" -H "cache-control: max-age=0" -H "dnt: 1" -H "upgrade-insecure-requests: 1" -H "user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36" -H "sec-fetch-user: ?1" -H "accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9" -H "sec-fetch-site: none" -H "sec-fetch-mode: navigate" -H "accept-encoding: gzip, deflate, br" -H "accept-language: en-US,en;q=0.9,hi;q=0.8" --compressed"""

INDICES: list[str] = ["NIFTY", "FINNIFTY", "BANKNIFTY"]
NSE_LIST: list[str] = ["NIFTY", "NIFTYIT", "BANKNIFTY"]

COMPACT_OI_MODE_COLUMN_NAMES: list[str] = [
    "CALLS_OI",
    "CALLS_Chng in OI",
    "CALLS_Volume",
    "CALLS_IV",
    "CALLS_LTP",
    "CALLS_Net Chng",
    "Strike Price",
    "PUTS_OI",
    "PUTS_Chng in OI",
    "PUTS_Volume",
    "PUTS_IV",
    "PUTS_LTP",
    "PUTS_Net Chng",
]
FULL_OI_MODE_COLUMN_NAMES: list[str] = [
    "CALLS_Chart",
    "CALLS_OI",
    "CALLS_Chng in OI",
    "CALLS_Volume",
    "CALLS_IV",
    "CALLS_LTP",
    "CALLS_Net Chng",
    "CALLS_Bid Qty",
    "CALLS_Bid Price",
    "CALLS_Ask Price",
    "CALLS_Ask Qty",
    "Strike Price",
    "PUTS_Bid Qty",
    "PUTS_Bid Price",
    "PUTS_Ask Price",
    "PUTS_Ask Qty",
    "PUTS_Net Chng",
    "PUTS_LTP",
    "PUTS_IV",
    "PUTS_Volume",
    "PUTS_Chng in OI",
    "PUTS_OI",
    "PUTS_Chart",
]
