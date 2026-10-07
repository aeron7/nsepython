import os,sys
#os.chdir(os.path.dirname(os.path.abspath(__file__)))
#sys.path.insert(1, os.path.join(sys.path[0], '..'))

import requests
import pandas as pd
import json
import random
import datetime,time
import logging
import re
import io
import urllib.parse

mode ='local'

# ---------------------------------------------------------------------------
# Transport
#
# NSE's site is fronted by Akamai Bot Manager, which fingerprints the TLS/JA3
# handshake of the client. A plain `requests.Session()` (or a shelled-out
# plain `curl`) gets blocked outright (HTTP 403 on the homepage itself) --
# this is NOT "requests is blocked in India", it's a bot-detection block that
# has nothing to do with geography. curl_cffi is a requests-compatible
# Session that impersonates a real Chrome TLS fingerprint, which clears this
# wall while remaining a pure Python HTTP client (no shell-out, no browser).
#
# curl_cffi is therefore the one and only transport nsefetch() uses now. It
# is a hard dependency (see requirements.txt/setup.py) because it's what
# makes the large majority of this library's functions work at all against
# the live site today.
# ---------------------------------------------------------------------------

try:
    from curl_cffi.requests import Session as _CurlSession
    _CURL_CFFI_OK = True
except ImportError:
    _CURL_CFFI_OK = False


class NSEEndpointError(Exception):
    """Raised by nsefetch() when NSE's site cannot be reached, or responds
    with something other than usable JSON (blocked, retired endpoint, rate
    limited, server error, etc).

    Older versions of this library silently swallowed these failures and
    returned `{}`, which just pushed the problem one level down into a
    confusing `KeyError`/`AttributeError` in whatever function called
    nsefetch() (see github.com/aeron7/nsepython issues #74, #75, and
    nsepythonserver #6). Raising a descriptive exception here instead makes
    the real failure visible immediately instead of as a downstream KeyError.
    """
    pass


_nse_session = None
_nse_warmed = False


def _get_nse_session():
    """Return the shared, warmed-up curl_cffi session used by nsefetch().

    The warm-up (visiting the homepage, then the option-chain page) is what
    gets NSE's Akamai Bot Manager to hand out the `nsit`/`_abck`/`ak_bmsc`/
    `bm_sv` cookies that most JSON API calls expect to see on the request.
    """
    global _nse_session, _nse_warmed

    if not _CURL_CFFI_OK:
        raise ImportError(
            "nsepython needs curl_cffi to talk to the real nseindia.com site. "
            "A plain `requests` session (and plain `curl`) gets blocked by "
            "NSE's Akamai Bot Manager purely on TLS fingerprint, regardless "
            "of where you are. Install it with: pip install curl_cffi"
        )

    if _nse_session is None:
        _nse_session = _CurlSession(impersonate="chrome124")

    if not _nse_warmed:
        try:
            _nse_session.get("https://www.nseindia.com", headers=headers, timeout=20)
            time.sleep(1.2)
            _nse_session.get("https://www.nseindia.com/option-chain", headers=headers, timeout=20)
            time.sleep(0.8)
            _nse_warmed = True
        except Exception as e:
            logging.warning("NSE session warm-up failed/partial: %s", e)

    return _nse_session


def _equity_stockindices_fallback(session, api_headers):
    """`/api/equity-stockIndices?index=SECURITIES IN F%26O` -- the F&O
    securities list used by fnolist()/nsetools_get_quote()/
    nse_get_advances_declines()/nse_get_top_losers()/nse_get_top_gainers()/
    nse_custom_function_secfno() -- is a retired route on the live site
    (confirmed HTTP 404, NSE's own "Resource not found" page, with or
    without a fully browser-solved Akamai cookie jar).

    `/api/market-data-pre-open?key=FO` carries the same per-symbol pChange/
    lastPrice/etc information for the F&O universe, so we transparently
    rewrite the request to that endpoint and reshape its response back into
    the old `{"data": [{"symbol":..., "pChange":..., ...}]}` shape every
    existing caller above already expects -- they keep working unchanged.
    """
    r = session.get(
        "https://www.nseindia.com/api/market-data-pre-open?key=FO",
        headers=api_headers, timeout=30,
    )
    if r.status_code != 200:
        raise NSEEndpointError(
            f"equity-stockIndices fallback (market-data-pre-open) failed: HTTP {r.status_code}"
        )
    try:
        raw = r.json()
    except ValueError:
        raise NSEEndpointError("equity-stockIndices fallback returned a non-JSON body")

    reshaped = []
    for item in raw.get("data", []):
        m = item.get("metadata", {}) or {}
        if not m.get("symbol"):
            continue
        reshaped.append({
            "symbol": m.get("symbol", ""),
            "pChange": m.get("pChange", 0),
            "lastPrice": m.get("lastPrice", 0),
            "change": m.get("change", 0),
            "previousClose": m.get("previousClose", 0),
            "yearHigh": m.get("yearHigh", 0),
            "yearLow": m.get("yearLow", 0),
            "totalTradedValue": m.get("totalTurnover", 0),
            "totalTradedVolume": m.get("finalQuantity", 0),
        })
    return {"data": reshaped}


def nsefetch(payload: str):
    """Fetch a nseindia.com JSON API URL through a warmed-up curl_cffi
    session, retrying once with a fresh warm-up if the first attempt looks
    blocked (stale/expired Akamai cookies), and raising NSEEndpointError
    (instead of silently returning `{}`) if it still can't get real JSON
    back. `mode` is kept only for backwards compatibility with older
    versions of this file; both 'local' and 'vpn' use this same transport
    now, since the previous mode='vpn' plain-curl/os.popen() implementation
    was both broken against the current Akamai wall *and* a command-injection
    risk (see github.com/aeron7/nsepython issue #73).
    """
    global _nse_warmed

    session = _get_nse_session()
    api_headers = dict(headers)
    api_headers.update({
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.nseindia.com/option-chain",
    })

    if "equity-stockIndices" in payload and "SECURITIES" in payload:
        return _equity_stockindices_fallback(session, api_headers)

    try:
        r = session.get(payload, headers=api_headers, timeout=30)
        if r.status_code in (401, 403, 404, 429, 503):
            # Could just be a stale/expired Akamai cookie jar -- re-warm once
            # and retry before giving up.
            _nse_warmed = False
            session = _get_nse_session()
            r = session.get(payload, headers=api_headers, timeout=30)

        if r.status_code != 200:
            raise NSEEndpointError(f"nsefetch: HTTP {r.status_code} for {payload}")

        try:
            return r.json()
        except ValueError:
            raise NSEEndpointError(
                f"nsefetch: NSE returned a non-JSON body (length={len(r.text)}) for {payload}"
            )
    except NSEEndpointError:
        raise
    except Exception as e:
        raise NSEEndpointError(f"nsefetch: request failed for {payload}: {e}")


# ---------------------------------------------------------------------------
# Optional, lazily-imported Playwright cookie-harvest fallback.
#
# For most of the library, curl_cffi's TLS impersonation + the warm-up above
# is all that's needed -- it is NOT the same as "requests is blocked", and it
# is NOT, in practice, gated behind a real JS-solved Akamai sensor challenge
# for the endpoints this library actually calls today (verified live: a
# fully browser-solved cookie jar makes zero difference to the handful of
# genuinely-retired routes like /api/quote-equity or /api/equity-stockIndices
# -- they are simply dead/404, not JS-walled).
#
# This helper exists as a best-effort escape hatch for the rarer case where
# NSE *does* flip an endpoint to require a cookie only a real browser's JS
# engine can produce -- curl_cffi never executes JavaScript, so it cannot
# solve that kind of challenge itself. It is intentionally NOT imported at
# module load time and NOT wired automatically into nsefetch(): it is slow
# (it launches a real headless browser), and for the specific endpoints this
# library has found still blocked as of this writing (the historical
# bulk/block/short-deals and securityArchives routes), the block looks like a
# server-side 503/retirement rather than a missing-JS-cookie problem, so
# there's no evidence a browser visit would fix them either. Call
# nse_harvest_playwright_cookies() yourself, once, near the start of your
# script if you want to try it against an endpoint you believe is genuinely
# JS-walled; it injects the solved cookies into the same shared session
# nsefetch() uses for every call after that.
# ---------------------------------------------------------------------------

def nse_harvest_playwright_cookies(url="https://www.nseindia.com/option-chain", timeout_ms=45000):
    """Launch a real headless Chromium (via Playwright), let it naturally
    pass NSE's Akamai Bot Manager JS sensor challenge by visiting `url`, then
    copy its solved cookie jar into the shared curl_cffi session nsefetch()
    uses. Optional, best-effort, and NOT required for the vast majority of
    this library's functions.

    Requires: pip install playwright && playwright install chromium
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise ImportError(
            "nse_harvest_playwright_cookies() needs Playwright to drive a "
            "real browser. Install it with: pip install playwright && "
            "playwright install chromium"
        ) from e

    session = _get_nse_session()
    harvested = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(user_agent=headers["User-Agent"])
            page.goto("https://www.nseindia.com", timeout=timeout_ms)
            page.wait_for_timeout(2000)
            page.goto(url, timeout=timeout_ms)
            page.wait_for_timeout(2000)
            for c in page.context.cookies():
                harvested[c["name"]] = c["value"]
        finally:
            browser.close()

    for name, value in harvested.items():
        try:
            session.cookies.set(name, value, domain=".nseindia.com")
        except Exception:
            pass

    global _nse_warmed
    _nse_warmed = True  # don't let the next nsefetch() stomp these with a plain re-warm
    return harvested


def _nse_fetch_csv_text(url: str) -> str:
    """Fetch a plain-text/CSV archive file through the shared curl_cffi
    session (so these also benefit from the TLS-impersonation fix and don't
    rely on plain `requests`/`pd.read_csv`'s bare urllib fetch, which
    confirmed-live testing shows just hangs/times out against
    nsearchives.nseindia.com, and is the less reliable of the two archive
    hosts generally as NSE tightens Akamai enforcement over time)."""
    session = _get_nse_session()
    r = session.get(url, headers=headers, timeout=30)
    if r.status_code != 200:
        raise NSEEndpointError(f"nsefetch (csv): HTTP {r.status_code} for {url}")
    return r.text


headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'DNT': '1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.79 Safari/537.36',
    'Sec-Fetch-User': '?1',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-Mode': 'navigate',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8',
}

#Curl headers
curl_headers = ''' -H "authority: beta.nseindia.com" -H "cache-control: max-age=0" -H "dnt: 1" -H "upgrade-insecure-requests: 1" -H "user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36" -H "sec-fetch-user: ?1" -H "accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9" -H "sec-fetch-site: none" -H "sec-fetch-mode: navigate" -H "accept-encoding: gzip, deflate, br" -H "accept-language: en-US,en;q=0.9,hi;q=0.8" --compressed'''

run_time=datetime.datetime.now()

#Constants
#
# Round 3: NSE has since added live F&O index-derivative products beyond
# the original 3 (confirmed live -- getSymbolDerivativesData&symbol=
# MIDCPNIFTY and &symbol=NIFTYNXT50 both return real, actively-traded
# CE/PE records right now, 2026-10). nse_quote()'s own `any(x in symbol
# for x in indices)` substring check already happened to work for these by
# accident (both names contain the substring "NIFTY"), but fnolist()'s
# exact-membership check (used by nse_quote_derivatives()) did not, which
# silently made nse_quote_ltp()/nse_quote_meta() return 0/{} for these
# symbols instead of real data. Listed explicitly here (not just relying on
# substring luck) so fnolist() membership works for them too.
indices = ['NIFTY','FINNIFTY','BANKNIFTY','MIDCPNIFTY','NIFTYNXT50']

def running_status():
    start_now=datetime.datetime.now().replace(hour=9, minute=15, second=0, microsecond=0)
    end_now=datetime.datetime.now().replace(hour=15, minute=30, second=0, microsecond=0)
    return start_now<datetime.datetime.now()<end_now

#Getting FNO Symboles
def fnolist():
    positions = nsefetch('https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O')
    nselist = indices.copy()
    for x in range(len(positions['data'])):
        nselist.append(positions['data'][x]['symbol'])
    return nselist

def nsesymbolpurify(symbol):
    symbol = symbol.replace('&','%26') #URL Parse for Stocks Like M&M Finance
    return symbol

def nse_optionchain_scrapper(symbol):
    symbol = nsesymbolpurify(symbol)
    # Using getSymbolDerivativesData as it provides all expiries and strikes in one go
    url = f'https://www.nseindia.com/api/NextApi/apiClient/GetQuoteApi?functionName=getSymbolDerivativesData&symbol={symbol}'
    payload = nsefetch(url)
    
    # Transformation to match the "data" structure expected by pcr and other functions
    if payload and 'data' in payload:
        new_data = []
        # Group by strikePrice and expiryDate to create a combined CE/PE structure if possible,
        # or just provide the raw list if the consumers can handle it.
        # The current pcr() handles a list of entries where each has CE/PE keys OR is the entry itself.
        
        # Actually, let's restructure it to be more compatible with the expected 'data' format:
        # a list of dictionaries, each having 'strikePrice', 'expiryDate', 'CE', 'PE'.
        combined = {}
        for entry in payload['data']:
            sp = entry.get('strikePrice')
            ed = entry.get('expiryDate')
            ot = entry.get('optionType')
            if not sp or not ed or ot == 'XX': continue
            
            key = (sp, ed)
            if key not in combined:
                combined[key] = {'strikePrice': sp, 'expiryDate': ed, 'CE': None, 'PE': None}
            
            combined[key][ot] = entry
            
        payload['data'] = list(combined.values())
        
    return payload


def oi_chain_builder(symbol,expiry="latest",oi_mode="full"):

    if expiry == "latest":
        dates = expiry_list(symbol, type="list")
        if dates:
            expiry = dates[0]
        else:
            return pd.DataFrame(), 0.0, ""

    payload = nse_optionchain_scrapper(symbol)

    if(oi_mode=='compact'):
        col_names = ['CALLS_OI','CALLS_Chng in OI','CALLS_Volume','CALLS_IV','CALLS_LTP','CALLS_Net Chng','Strike Price','PUTS_OI','PUTS_Chng in OI','PUTS_Volume','PUTS_IV','PUTS_LTP','PUTS_Net Chng']
    if(oi_mode=='full'):
        col_names = ['CALLS_Chart','CALLS_OI','CALLS_Chng in OI','CALLS_Volume','CALLS_IV','CALLS_LTP','CALLS_Net Chng','CALLS_Bid Qty','CALLS_Bid Price','CALLS_Ask Price','CALLS_Ask Qty','Strike Price','PUTS_Bid Qty','PUTS_Bid Price','PUTS_Ask Price','PUTS_Ask Qty','PUTS_Net Chng','PUTS_LTP','PUTS_IV','PUTS_Volume','PUTS_Chng in OI','PUTS_OI','PUTS_Chart']
    oi_data = pd.DataFrame(columns = col_names)

    # We will populate these dynamically
    rows_list = []
    
    if 'expiryDates' not in payload:
        # Fallback for new API structure
        if(expiry=="latest"):
            expiry = expiry_list(symbol, type="list")[0]
        data_list = payload['data']
    else:
        # Legacy structure support
        if(expiry=="latest"):
            expiry = payload['records']['expiryDates'][0]
        data_list = payload['records']['data']

    for m in range(len(data_list)):
        current_expiry_str = data_list[m].get('expiryDates') or data_list[m].get('expiryDate')
        try:
            # Convert both to date objects for robust comparison
            if "-" in current_expiry_str:
                parts = current_expiry_str.split("-")
                if parts[1].isdigit(): fmt = "%d-%m-%Y"
                else: fmt = "%d-%b-%Y"
                curr_date = datetime.datetime.strptime(current_expiry_str, fmt).date()
                
                parts_exp = expiry.split("-")
                if parts_exp[1].isdigit(): fmt_exp = "%d-%m-%Y"
                else: fmt_exp = "%d-%b-%Y"
                exp_date = datetime.datetime.strptime(expiry, fmt_exp).date()
                match = (curr_date == exp_date)
            else:
                match = (current_expiry_str == expiry)
        except:
            match = (current_expiry_str == expiry)

        if match:
            oi_row = {col: 0 for col in col_names}
            oi_row['Strike Price'] = data_list[m]['strikePrice']

            for side in ['CE', 'PE']:
                prefix = f"{'CALLS' if side == 'CE' else 'PUTS'}_"
                if side in data_list[m] and data_list[m][side] is not None:
                    d = data_list[m][side]
                    oi_row[prefix + 'OI'] = d.get('openInterest', 0)
                    oi_row[prefix + 'Chng in OI'] = d.get('changeinOpenInterest', 0)
                    oi_row[prefix + 'Volume'] = d.get('totalTradedVolume', 0)
                    oi_row[prefix + 'IV'] = d.get('impliedVolatility', 0)
                    oi_row[prefix + 'LTP'] = d.get('lastPrice', 0)
                    oi_row[prefix + 'Net Chng'] = d.get('change', 0)
                    
                    if oi_mode == 'full':
                        # New API key mapping
                        oi_row[prefix + 'Bid Qty'] = d.get('buyQuantity1', d.get('bidQty', 0))
                        oi_row[prefix + 'Bid Price'] = d.get('buyPrice1', d.get('bidprice', 0))
                        oi_row[prefix + 'Ask Price'] = d.get('sellPrice1', d.get('askPrice', 0))
                        oi_row[prefix + 'Ask Qty'] = d.get('sellQuantity1', d.get('askQty', 0))
                        oi_row[prefix + 'Chart'] = 0

            rows_list.append(oi_row)

    oi_data = pd.DataFrame(rows_list)
    timestamp = payload.get('timestamp', payload.get('records', {}).get('timestamp', ''))
    underlyingValue = payload.get('underlyingValue', payload.get('records', {}).get('underlyingValue', 0))

    # github.com/aeron7/nsepython issue #80: the current getSymbolDerivativesData
    # payload carries no top-level (or 'records') underlyingValue at all -- it
    # only lives inside each individual CE/PE leaf record. Dig it out of there
    # if the top-level lookup above came back empty.
    if not underlyingValue and data_list:
        for entry in data_list:
            for side in ('CE', 'PE'):
                leaf = entry.get(side)
                if leaf and leaf.get('underlyingValue'):
                    underlyingValue = leaf['underlyingValue']
                    break
            if underlyingValue:
                break

    oi_data['time_stamp'] = timestamp
    return oi_data, float(underlyingValue or 0), timestamp


def nse_quote_derivatives(symbol):
    symbol = nsesymbolpurify(symbol)
    # Round 3 bug fix: the membership check below was correctly
    # case-insensitive (symbol.upper() in fnolist()) but the URL built right
    # after it used the original, un-uppercased `symbol` -- the live
    # getSymbolDerivativesData endpoint is itself case-sensitive, so a
    # lowercase/mixed-case symbol (e.g. "sbin", "banknifty") silently came
    # back as {'data': [], 'timestamp': ''} (a plausible-looking empty
    # response, not an error) instead of real data. Uppercase once and reuse
    # it for both the check and the fetch.
    symbol_u = symbol.upper()
    if symbol_u in fnolist():
        payload = nsefetch('https://www.nseindia.com/api/NextApi/apiClient/GetQuoteApi?functionName=getSymbolDerivativesData&symbol='+symbol_u)
        return payload
    else:
        return {"error": f"{symbol} is not in derivatives list."}

def nse_quote(symbol,section=""):
    #https://forum.unofficed.com/t/nsetools-get-quote-is-not-fetching-delivery-data-and-delivery-can-you-include-this-as-part-of-feature-request/1115/4
    #
    # section='' (default) already returns the FULL detail in one call --
    # metaData/secInfo/priceInfo/orderBook/tradeInfo are all present together
    # in that single payload. Only pass section= for a genuine sub-slice:
    #   'trade_info'    -- order-book depth / VaR margin slice
    #   'preOpenMarket' -- the day's 09:00-09:08 IST pre-open auction ladder
    # Round 3 research (checked against unofficed.com's own docs, the
    # hi-imcodeman/stock-nse-india reference TS implementation, and this
    # project's entire GitHub issue history) found no evidence NSE's old API
    # ever accepted any OTHER section= value -- 'preOpenMarket'/'metadata'/
    # 'industryInfo'/'info'/'priceInfo'/'securityInfo' were never alternate
    # query values, just top-level keys inside the un-sectioned response
    # section='' already returns.
    symbol = nsesymbolpurify(symbol)
    # Round 3 bug fix: this substring check used to be case-sensitive, so a
    # lowercase/mixed-case index name (e.g. "banknifty") fell through to the
    # equity branch below and 404'd (banknifty isn't an equity symbol).
    symbol_u = symbol.upper()

    if(section==""):
        if any(x in symbol_u for x in indices):
            payload = nsefetch('https://www.nseindia.com/api/NextApi/apiClient/GetQuoteApi?functionName=getSymbolDerivativesData&symbol='+symbol_u)
        else:
            payload = nsefetch('https://www.nseindia.com/api/NextApi/apiClient/GetQuoteApi?functionName=getSymbolData&marketType=N&series=EQ&symbol='+symbol_u)
        return payload

    if(section=="trade_info"):
        # The old /api/quote-equity?section=trade_info route is dead on the
        # live site (confirmed HTTP 403, even through the fully-warmed
        # curl_cffi session round 1 built). But every category of data the
        # old endpoint used to return is already present, just reshuffled,
        # inside the NEW working GetQuoteApi?functionName=getSymbolData
        # response this function's section=="" branch already fetches --
        # confirmed field-by-field against the real, documented old
        # response shape (EquityTradeInfo: marketDeptOrderBook.{bid,ask,
        # tradeInfo,valueAtRisk} + securityWiseDP), so this is a pure
        # remap/slice of data already being fetched, not a new network call.
        #
        # Two small fidelity gaps versus the old route, both because the
        # source data for them no longer exists anywhere in the new
        # response (not a mapping oversight):
        #   - noBlockDeals/bulkBlockDeals: the new endpoint carries no
        #     block-deal info at all -> defaulted to True/[] (i.e. "no
        #     block deals known"), not derived from a live block-deal
        #     check. Use nse_blockdeal()/get_blockdeals() directly if you
        #     need real block-deal data.
        #   - securityWiseDP.seriesRemarks: no equivalent field exists in
        #     the new response -> always None, same as it is for most
        #     symbols on the old route anyway.
        payload = nsefetch('https://www.nseindia.com/api/NextApi/apiClient/GetQuoteApi?functionName=getSymbolData&marketType=N&series=EQ&symbol='+symbol_u)
        if 'equityResponse' not in payload or not payload['equityResponse']:
            raise NSEEndpointError(
                f"nse_quote({symbol!r}, section='trade_info'): no "
                f"equityResponse in payload -- this section is only "
                f"meaningful for an equity symbol (not an index/derivative "
                f"underlying)."
            )
        eq = payload['equityResponse'][0]
        ob = eq.get('orderBook', {})
        md = eq.get('metaData', {})
        ti = eq.get('tradeInfo', {})
        pi = eq.get('priceInfo', {})
        si = eq.get('secInfo', {})

        bid = [{"price": ob.get(f"buyPrice{i}"), "quantity": ob.get(f"buyQuantity{i}")} for i in range(1, 6)]
        ask = [{"price": ob.get(f"sellPrice{i}"), "quantity": ob.get(f"sellQuantity{i}")} for i in range(1, 6)]

        return {
            "noBlockDeals": True,
            "bulkBlockDeals": [],
            "marketDeptOrderBook": {
                "totalBuyQuantity": ob.get("totalBuyQuantity"),
                "totalSellQuantity": ob.get("totalSellQuantity"),
                "open": md.get("open"),
                "bid": bid,
                "ask": ask,
                "tradeInfo": {
                    "totalTradedVolume": ti.get("totalTradedVolume"),
                    "totalTradedValue": ti.get("totalTradedValue"),
                    "totalMarketCap": ti.get("totalMarketCap"),
                    "ffmc": ti.get("ffmc"),
                    "impactCost": ti.get("impactCost"),
                    "cmDailyVolatility": pi.get("cmDailyVolatility"),
                    "cmAnnualVolatility": pi.get("cmAnnualVolatility"),
                    "marketLot": ti.get("marketLot"),
                    "activeSeries": ti.get("series"),
                },
                "valueAtRisk": {
                    "securityVar": si.get("securityvar"),
                    "indexVar": si.get("indexvar"),
                    "varMargin": si.get("varMargin"),
                    "extremeLossMargin": si.get("extremelossMargin"),
                    "adhocMargin": si.get("adhocMargin"),
                    "applicableMargin": si.get("applicableMargin"),
                },
            },
            "securityWiseDP": {
                "quantityTraded": ti.get("quantitytraded"),
                "deliveryQuantity": ti.get("deliveryquantity"),
                "deliveryToTradedQuantity": ti.get("deliveryToTradedQuantity"),
                "seriesRemarks": None,
                "secWiseDelPosDate": ti.get("secwisedelposdate"),
            },
        }

    if(section=="preOpenMarket"):
        # Round 3: NSE's old /api/quote-equity&section=preOpenMarket route
        # is dead (confirmed HTTP 403, same wall as every other section
        # value below), but a genuinely live, working replacement exists:
        # /api/market-data-pre-open?key=ALL returns ALL ~2200 symbols' real
        # pre-open order-book ladders in one shot. Filter it down to the
        # requested symbol instead of fabricating anything.
        #
        # Caveat (documented, not disguised): this is literally the
        # 09:00-09:08 IST pre-open auction snapshot, not continuous/live
        # intraday data -- checked well after market open it will look
        # "stale" because it reflects that morning's last pre-open auction.
        # That is the real, live content of this feed, not a bug.
        payload = nsefetch('https://www.nseindia.com/api/market-data-pre-open?key=ALL')
        for entry in payload.get('data', []):
            if entry.get('metadata', {}).get('symbol') == symbol_u:
                return entry['detail']['preOpenMarket']
        raise NSEEndpointError(
            f"nse_quote({symbol!r}, section='preOpenMarket'): {symbol_u} was "
            f"not found in today's pre-open-market list -- either it isn't a "
            f"pre-open-eligible series, or today's pre-open session hasn't "
            f"run/populated yet."
        )

    # Round 3: every other section value (e.g. the old 'metadata'/
    # 'industryInfo'/'info'/'priceInfo'/'securityInfo') used to fall through
    # here and hit the dead /api/quote-equity&section=X route -- a ~5s
    # double-retry ending in a misleading HTTP 403, for a route that was
    # never real in the first place. Checked against unofficed.com's own
    # docs, the hi-imcodeman/stock-nse-india reference implementation, and
    # this project's full GitHub issue history: NSE's API never accepted
    # any section value beyond 'trade_info' -- those other names are just
    # top-level keys inside the un-sectioned response, already returned in
    # full by nse_quote(symbol) (section=""). Raise immediately and clearly
    # instead of a slow, confusing network round-trip to a route that was
    # never real.
    raise ValueError(
        f"nse_quote: unsupported section={section!r}; only '' (full quote), "
        f"'trade_info', and 'preOpenMarket' are supported -- NSE's old "
        f"quote-equity API never had other section values. section='' "
        f"already returns the full detail (metaData/secInfo/priceInfo/"
        f"orderBook/tradeInfo all together)."
    )
def nse_expirydetails(payload, i=0, symbol=None):
    expiry_dates = []
    if 'records' in payload:
        expiry_dates = payload['records']['expiryDates']
    elif 'expiryDates' in payload:
        expiry_dates = payload['expiryDates']
    elif 'data' in payload:
        unique_dates = set()
        for entry in payload['data']:
            if 'expiryDate' in entry:
                unique_dates.add(entry['expiryDate'])
        expiry_dates = sorted(list(unique_dates), key=lambda x: datetime.datetime.strptime(x, "%d-%b-%Y"))

    # Filter future dates
    future_expiry_dates = []
    if expiry_dates:
        temp_dates = [datetime.datetime.strptime(date, "%d-%b-%Y").date() for date in expiry_dates]
        future_expiry_dates = sorted([date.strftime("%d-%b-%Y") for date in temp_dates if date >= datetime.datetime.now().date()], key=lambda x: datetime.datetime.strptime(x, "%d-%b-%Y"))

    # Fallback to expiry_list if i is out of range and we can determine the symbol
    if i >= len(future_expiry_dates):
        if not symbol and 'data' in payload and len(payload['data']) > 0:
            # Try to extract symbol from payload data
            first_entry = payload['data'][0]
            symbol = first_entry.get('symbol')
            if not symbol:
                if 'CE' in first_entry and first_entry['CE']:
                    symbol = first_entry['CE'].get('underlying')
                elif 'PE' in first_entry and first_entry['PE']:
                    symbol = first_entry['PE'].get('underlying')
        
        if symbol:
            dates = expiry_list(symbol, type="list")
            if dates:
                # Filter future dates from expiry_list as well
                temp_dates = [datetime.datetime.strptime(date, "%d-%b-%Y").date() for date in dates]
                future_expiry_dates = sorted([date.strftime("%d-%b-%Y") for date in temp_dates if date >= datetime.datetime.now().date()], key=lambda x: datetime.datetime.strptime(x, "%d-%b-%Y"))

    if i >= len(future_expiry_dates):
        return None, None

    currentExpiry = future_expiry_dates[i]
    currentExpiry_dt = datetime.datetime.strptime(currentExpiry, '%d-%b-%Y').date()
    date_today = run_time.date()
    dte = (currentExpiry_dt - date_today).days
    return currentExpiry_dt, dte

def _pcr_entry_oi(entry):
    """Round 3 fix: pcr() must accept BOTH option-chain shapes this library
    can hand it --
      - the NESTED per-strike shape nse_optionchain_scrapper()/option_chain()
        return: {'strikePrice','expiryDate','CE':{...},'PE':{...}}
      - the FLAT per-contract-leg shape nse_quote_derivatives()/nse_quote()
        (for derivatives) actually return now: each entry IS one leg
        directly, with optionType=='CE'/'PE' and openInterest at the TOP
        LEVEL -- there is no nested entry['CE']/entry['PE'] in this shape at
        all.
    Before this fix, pcr()'s aggregation loop only ever read entry['CE']/
    entry['PE'], so feeding it the flat shape matched the target expiry
    (found_data=True) but silently added 0 to both ce_oi/pe_oi every time,
    returning a plausible-looking-but-wrong pcr of 0.0 instead of raising.
    Returns (ce_oi_contribution, pe_oi_contribution) for one entry.
    """
    if ('CE' in entry) or ('PE' in entry):
        ce = entry['CE'].get('openInterest', 0) or 0 if entry.get('CE') else 0
        pe = entry['PE'].get('openInterest', 0) or 0 if entry.get('PE') else 0
        return ce, pe
    if entry.get('optionType') == 'CE':
        return entry.get('openInterest', 0) or 0, 0
    if entry.get('optionType') == 'PE':
        return 0, entry.get('openInterest', 0) or 0
    return 0, 0

def pcr(payload, inp=0):
    ce_oi = 0
    pe_oi = 0

    # Identify the data and expiry dates based on structure
    if 'records' in payload:
        # Legacy structure
        data_list = payload['records']['data']
        expiry_dates = payload['records']['expiryDates']
    elif 'data' in payload:
        # New structure (covers BOTH the nested per-strike shape and the
        # flat per-contract-leg shape -- see _pcr_entry_oi() above)
        data_list = payload['data']
        # Extract unique sorted expiry dates from data
        unique_dates = set()
        for entry in data_list:
            ed = entry.get('expiryDate') or entry.get('expiryDates')
            if ed:
                unique_dates.add(ed)
        expiry_dates = sorted(list(unique_dates), key=lambda x: datetime.datetime.strptime(x, "%d-%m-%Y") if "-" in x and x.split("-")[1].isdigit() else datetime.datetime.strptime(x, "%d-%b-%Y"))
    else:
        # Round 3: a payload with neither 'records' nor 'data' isn't a
        # recognizable option-chain/derivatives shape at all -- returning
        # 0.0 here used to silently look like "zero put/call OI" instead of
        # "this isn't option-chain data". Raise clearly instead.
        raise NSEEndpointError(
            "pcr(): payload has neither 'records' nor 'data' -- pass the "
            "output of option_chain()/nse_optionchain_scrapper(), "
            "nse_quote_derivatives(), or nse_quote() for a derivatives "
            "symbol."
        )

    if not expiry_dates or inp >= len(expiry_dates):
        # Requested index is outside the current payload's scope.
        # Check if we can fetch more data for this specific symbol.
        symbol = payload.get('symbol') or payload.get('records', {}).get('symbol')
        if not symbol and 'data' in payload and len(payload['data']) > 0:
             first = payload['data'][0]
             symbol = (first.get('symbol') or first.get('underlying')
                       or (first.get('CE') and first['CE'].get('underlying'))
                       or (first.get('PE') and first['PE'].get('underlying')))

        if symbol and inp > 0:
            # Fetch all expiries to find the target one
            all_expiries = expiry_list(symbol, type="list")
            if inp < len(all_expiries):
                target = all_expiries[inp]
                # Fetch specific expiry data using getOptionChainData
                url = f'https://www.nseindia.com/api/NextApi/apiClient/GetQuoteApi?functionName=getOptionChainData&symbol={nsesymbolpurify(symbol)}&params=expiryDate={target}'
                new_payload = nsefetch(url)
                if new_payload and 'data' in new_payload:
                    for entry in new_payload['data']:
                        ce_oi += entry.get('CE', {}).get('openInterest', 0) if entry.get('CE') else 0
                        pe_oi += entry.get('PE', {}).get('openInterest', 0) if entry.get('PE') else 0
                    if ce_oi > 0: return pe_oi / ce_oi
        return 0.0
        
    target_expiry = expiry_dates[inp]

    found_data = False
    for i in data_list:
        curr_exp = i.get('expiryDate') or i.get('expiryDates')
        if curr_exp == target_expiry:
            found_data = True
            try:
                c, p = _pcr_entry_oi(i)
                ce_oi += c
                pe_oi += p
            except (KeyError, TypeError):
                pass
    
    # If we didn't find any data for the target expiry in the payload,
    # it means the payload was filtered (e.g. by the scrapper). Fetch it now.
    if not found_data:
        symbol = payload.get('symbol') or payload.get('records', {}).get('symbol')
        if symbol:
            url = f'https://www.nseindia.com/api/NextApi/apiClient/GetQuoteApi?functionName=getOptionChainData&symbol={nsesymbolpurify(symbol)}&params=expiryDate={target_expiry}'
            new_payload = nsefetch(url)
            if new_payload and 'data' in new_payload:
                for entry in new_payload['data']:
                    ce_oi += entry.get('CE', {}).get('openInterest', 0) if entry.get('CE') else 0
                    pe_oi += entry.get('PE', {}).get('openInterest', 0) if entry.get('PE') else 0

    if ce_oi == 0:
        return 0.0
        
    return pe_oi / ce_oi

#forum.unofficed.com/t/unable-to-find-nse-quote-meta-api/702/4
#Refer https://forum.unofficed.com/t/changed-the-nse-quote-ltp-function/1276
def nse_quote_ltp(symbol,expiryDate="latest",optionType="-",strikePrice=0):
  # Round 3 bug fix: this index-routing check was case-sensitive, so e.g.
  # nse_quote_ltp("banknifty") (no optionType) missed the indices branch,
  # fell through to the equity getSymbolData endpoint, and 404'd. Checking
  # against symbol.upper() routes it correctly regardless of case.
  if(optionType!="-"):
      payload = nse_quote_derivatives(symbol)
  else:
      if any(x in symbol.upper() for x in indices):
          payload = nse_quote_derivatives(symbol)
      else:
          payload = nsefetch('https://www.nseindia.com/api/NextApi/apiClient/GetQuoteApi?functionName=getSymbolData&marketType=N&series=EQ&symbol='+symbol.upper())

  lastPrice = 0

  if(optionType=="-"):
    if 'equityResponse' in payload and len(payload['equityResponse']) > 0:
        lastPrice = payload['equityResponse'][0]['orderBook']['lastPrice']
    elif 'data' in payload and len(payload['data']) > 0:
        # For indices, underlyingValue in derivative payload is the current index LTP
        lastPrice = payload['data'][0].get('underlyingValue')
    return lastPrice

  meta = "Options"
  if(optionType=="Fut"): meta = "Futures"
  if(optionType=="PE"):optionType="Put"
  if(optionType=="CE"):optionType="Call"

  if(expiryDate=="latest") or (expiryDate=="next"):
    i = 0 if expiryDate=="latest" else 1
    expiry_dates = []
    
    # Extract from new FNO payload structure
    if 'data' in payload:
        unique_dates = set()
        for entry in payload['data']:
            if 'expiryDate' in entry:
                it = entry.get('instrumentType', '')
                if (meta == "Futures" and "FUT" in it) or (meta == "Options" and "OPT" in it):
                    unique_dates.add(entry['expiryDate'])
        expiry_dates = sorted(list(unique_dates), key=lambda x: datetime.datetime.strptime(x, "%d-%b-%Y"))
    
    # Filter future dates
    future_expiry_dates = []
    if expiry_dates:
        temp_dates = [datetime.datetime.strptime(date, "%d-%b-%Y").date() for date in expiry_dates]
        future_expiry_dates = sorted([date.strftime("%d-%b-%Y") for date in temp_dates if date >= datetime.datetime.now().date()], key=lambda x: datetime.datetime.strptime(x, "%d-%b-%Y"))

    # Fallback to expiry_list
    if i >= len(future_expiry_dates):
        dates = expiry_list(symbol, type="list")
        if dates:
            temp_dates = [datetime.datetime.strptime(date, "%d-%b-%Y").date() for date in dates]
            future_expiry_dates = sorted([date.strftime("%d-%b-%Y") for date in temp_dates if date >= datetime.datetime.now().date()], key=lambda x: datetime.datetime.strptime(x, "%d-%b-%Y"))
    
    if i < len(future_expiry_dates):
        expiryDate = future_expiry_dates[i]
  

  if(optionType!="-"):
      data_list = payload.get('data', [])
      for i in data_list:
        # Check instrument type in identifier or metadata if present
        if meta == "Futures":
            is_match = "FUT" in i.get('instrumentType', '')
        else:
            is_match = "OPT" in i.get('instrumentType', '')
            
        if is_match:
          if(optionType=="Fut"):
              if(i.get('expiryDate')==expiryDate):
                lastPrice = i.get('lastPrice')
                break

          if((optionType=="Put")or(optionType=="Call")):
              # Some APIs have optionType as 'PE'/'CE' or 'Put'/'Call'
              p_opt_type = i.get('optionType')
              if p_opt_type == "PE": p_opt_type = "Put"
              if p_opt_type == "CE": p_opt_type = "Call"
              
              if (i.get("expiryDate")==expiryDate):
                if (p_opt_type==optionType):
                  # strikePrice in payload is often string with padding
                  try:
                      p_strike = float(str(i.get("strikePrice")).strip())
                  except:
                      p_strike = 0
                      
                  if (p_strike==float(strikePrice)):
                    lastPrice = i.get('lastPrice')
                    break

  return lastPrice

# print(nse_quote_ltp("RELIANCE"))
# print(nse_quote_ltp("RELIANCE","latest","Fut"))
# print(nse_quote_ltp("RELIANCE","next","Fut"))
# print(nse_quote_ltp("BANKNIFTY","latest","PE",32000))
# print(nse_quote_ltp("BANKNIFTY","next","PE",32000))
# print(nse_quote_ltp("BANKNIFTY","10-Jun-2021","PE",32000))
# print(nse_quote_ltp("BANKNIFTY","17-Jun-2021","PE",32000))
# print(nse_quote_ltp("RELIANCE","latest","PE",2300))
# print(nse_quote_ltp("RELIANCE","next","PE",2300))

def nse_quote_meta(symbol,expiryDate="latest",optionType="-",strikePrice=0):
  # Round 3 bug fix: case-sensitive index routing (see nse_quote_ltp()).
  if(optionType!="-"):
      payload = nse_quote_derivatives(symbol)
  else:
      if any(x in symbol.upper() for x in indices):
          payload = nse_quote_derivatives(symbol)
      else:
          payload = nsefetch('https://www.nseindia.com/api/NextApi/apiClient/GetQuoteApi?functionName=getSymbolData&marketType=N&series=EQ&symbol='+symbol.upper())

  metadata = {}

  if(optionType=="-"):
      if 'equityResponse' in payload and len(payload['equityResponse']) > 0:
          metadata = payload['equityResponse'][0].get('metaData', {})
      elif 'data' in payload and len(payload['data']) > 0:
          # Round 3 fix (known gap #2): index/derivative underlyings go
          # through nse_quote_derivatives()'s flat per-contract-leg shape,
          # which has no 'equityResponse'/'metaData' at all -- this used to
          # silently fall through to the {} default, making every index
          # symbol look like "no data" instead of "wrong shape for this
          # accessor". There is no equity-style open/high/low/close
          # snapshot anywhere in this payload for an index (only
          # underlyingValue/underlying/timestamp per leg), so we return the
          # real fields that DO exist instead of fabricating the rest.
          first = payload['data'][0]
          metadata = {
              "symbol": first.get('underlying') or symbol.upper(),
              "underlyingValue": first.get('underlyingValue'),
              "timestamp": payload.get('timestamp'),
          }
      return metadata

  meta = "Options"
  if(optionType=="Fut"): meta = "Futures"
  if(optionType=="PE"):optionType="Put"
  if(optionType=="CE"):optionType="Call"

  if(expiryDate=="latest") or (expiryDate=="next"):
    i = 0 if expiryDate=="latest" else 1
    expiry_dates = []
    if 'data' in payload:
        unique_dates = set()
        for entry in payload['data']:
            if 'expiryDate' in entry:
                it = entry.get('instrumentType', '')
                if (meta == "Futures" and "FUT" in it) or (meta == "Options" and "OPT" in it):
                    unique_dates.add(entry['expiryDate'])
        expiry_dates = sorted(list(unique_dates), key=lambda x: datetime.datetime.strptime(x, "%d-%b-%Y"))
    
    future_expiry_dates = []
    if expiry_dates:
        temp_dates = [datetime.datetime.strptime(date, "%d-%b-%Y").date() for date in expiry_dates]
        future_expiry_dates = sorted([date.strftime("%d-%b-%Y") for date in temp_dates if date >= datetime.datetime.now().date()], key=lambda x: datetime.datetime.strptime(x, "%d-%b-%Y"))

    if i >= len(future_expiry_dates):
        dates = expiry_list(symbol, type="list")
        if dates:
            temp_dates = [datetime.datetime.strptime(date, "%d-%b-%Y").date() for date in dates]
            future_expiry_dates = sorted([date.strftime("%d-%b-%Y") for date in temp_dates if date >= datetime.datetime.now().date()], key=lambda x: datetime.datetime.strptime(x, "%d-%b-%Y"))
    
    if i < len(future_expiry_dates):
        expiryDate = future_expiry_dates[i]
    
    # print(f"DEBUG: Calculated expiryDate={expiryDate}, meta={meta}, optionType={optionType}")

  if(optionType!="-"):
      data_list = payload.get('data', [])
      # print(f"DEBUG: Searching in {len(data_list)} items")
      for i in data_list:
        if meta == "Futures":
            is_match = "FUT" in i.get('instrumentType', '')
        else:
            is_match = "OPT" in i.get('instrumentType', '')
            
        if is_match:
          if(optionType=="Fut"):
              if(i.get('expiryDate')==expiryDate):
                metadata = i
                break

          if((optionType=="Put")or(optionType=="Call")):
              p_opt_type = i.get('optionType')
              if p_opt_type == "PE": p_opt_type = "Put"
              if p_opt_type == "CE": p_opt_type = "Call"
              
              if (i.get("expiryDate")==expiryDate):
                if (p_opt_type==optionType):
                  try:
                      p_strike = float(str(i.get("strikePrice")).strip())
                  except:
                      p_strike = 0
                      
                  if (p_strike==float(strikePrice)):
                    metadata = i
                    break

  return metadata

def nse_optionchain_ltp(payload,strikePrice,optionType,inp=0,intent=""):
    # Round 3 bug fix (new finding, highest severity found this round): this
    # function unconditionally indexed payload['records'] -- the pre-rewrite
    # legacy NSE shape. option_chain()/nse_optionchain_scrapper() (this
    # library's OWN current option-chain source, since round 1) return
    # {'data': [...], 'timestamp': ...} instead -- 'records' doesn't exist
    # anywhere in the live code path any more, so this function could never
    # succeed with real data produced by this library: every call crashed
    # with KeyError('records'), unconditionally.
    if 'records' in payload:
        # Legacy shape, kept for any caller handing in an old-style cached
        # payload captured before this library's rewrite.
        expiry_dates = payload['records']['expiryDates']
        expiry_dates = [datetime.datetime.strptime(date, "%d-%b-%Y").date() for date in expiry_dates]
        expiry_dates = [date.strftime("%d-%b-%Y") for date in expiry_dates if date >= datetime.datetime.now().date()]
        if inp >= len(expiry_dates):
            raise NSEEndpointError(
                f"nse_optionchain_ltp(): requested expiry index {inp} is out "
                f"of range -- only {len(expiry_dates)} future expiries found."
            )
        expiryDate = expiry_dates[inp]
        for x in range(len(payload['records']['data'])):
            row = payload['records']['data'][x]
            if (row['strikePrice'] == strikePrice) and (row['expiryDate'] == expiryDate):
                leg = row[optionType]
                if(intent==""): return leg['lastPrice']
                if(intent=="sell"): return leg['bidprice']
                if(intent=="buy"): return leg['askPrice']
        return None

    if 'data' in payload:
        # Current shape: option_chain()/nse_optionchain_scrapper()'s flat
        # 'data' list, each entry already grouped per-strike with 'CE'/'PE'
        # sub-dicts (see nse_optionchain_scrapper()'s combine step) --
        # strikePrice/expiryDate live on the outer entry, the price fields
        # live inside entry[optionType].
        data_list = payload['data']

        def _parse_exp(d):
            try:
                if "-" in d and d.split("-")[1].isdigit():
                    return datetime.datetime.strptime(d, "%d-%m-%Y").date()
                return datetime.datetime.strptime(d, "%d-%b-%Y").date()
            except Exception:
                return None

        unique_dates = sorted(
            {e.get('expiryDate') for e in data_list if e.get('expiryDate')},
            key=lambda d: _parse_exp(d) or datetime.date.max,
        )
        today = datetime.datetime.now().date()
        future_dates = [d for d in unique_dates if (_parse_exp(d) or today) >= today]
        if inp >= len(future_dates):
            raise NSEEndpointError(
                f"nse_optionchain_ltp(): requested expiry index {inp} is out "
                f"of range -- only {len(future_dates)} future expiries found "
                f"in this payload."
            )
        expiryDate = future_dates[inp]

        try:
            target_strike = float(str(strikePrice).strip())
        except Exception:
            target_strike = None

        for entry in data_list:
            if entry.get('expiryDate') != expiryDate:
                continue
            try:
                entry_strike = float(str(entry.get('strikePrice')).strip())
            except Exception:
                continue
            if target_strike is not None and entry_strike != target_strike:
                continue
            if 'optionType' in entry and 'CE' not in entry and 'PE' not in entry:
                # Flat per-leg shape (nse_quote_derivatives()/nse_quote()'s
                # getSymbolDerivativesData output): each list entry IS one
                # CE or PE leg directly (entry['optionType'] == 'CE'/'PE',
                # price fields on the entry itself) rather than one entry
                # per strike holding both legs nested under entry['CE']/
                # entry['PE']. Round-3 bug (confirmed live, fixed here):
                # entry.get(optionType) always returned None for this shape
                # since there's no such nested key on a flat leg.
                if entry.get('optionType') != optionType:
                    continue
                leg = entry
            else:
                leg = entry.get(optionType)
            if not leg:
                continue
            if intent == "":
                return leg.get('lastPrice')
            if intent == "sell":
                # The live getSymbolDerivativesData-backed payload carries
                # no bid/ask order-book fields at all (confirmed live) --
                # only the legacy 'records' shape had bidprice/askPrice.
                # This is a genuine data-availability gap, not a lookup
                # bug: returns None rather than guessing a price.
                return leg.get('buyPrice1', leg.get('bidprice'))
            if intent == "buy":
                return leg.get('sellPrice1', leg.get('askPrice'))
        return None

    raise NSEEndpointError(
        "nse_optionchain_ltp(): payload has neither 'records' nor 'data' -- "
        "pass the output of option_chain()/nse_optionchain_scrapper() "
        "directly."
    )

def nse_eq(symbol):
    symbol = nsesymbolpurify(symbol)
    try:
        payload = nsefetch('https://www.nseindia.com/api/quote-equity?symbol='+symbol)
        try:
            if(payload['error']=={}):
                print("Please use nse_fno() function to reduce latency.")
                payload = nsefetch('https://www.nseindia.com/api/quote-derivative?symbol='+symbol)
        except:
            pass
    except (KeyError, NSEEndpointError):
        # /api/quote-equity is retired on the live site (confirmed HTTP 403,
        # Akamai/WAF "Access Denied" page, as of 2026) with no indication it
        # is coming back. The newer NextApi GetQuoteApi endpoint carries the
        # same underlying data (just in a different JSON shape - data lives
        # under payload['equityResponse'][0] instead of payload['priceInfo']/
        # payload['info']) so we fall back to that instead of returning {}.
        logging.warning(
            "nse_eq(%s): /api/quote-equity is retired; returning data from "
            "the newer NextApi quote endpoint instead (see nse_quote() - the "
            "JSON shape differs from the old quote-equity response).",
            symbol,
        )
        payload = nse_quote(symbol)
    return payload


def nse_fno(symbol):
    symbol = nsesymbolpurify(symbol)
    try:
        payload = nsefetch('https://www.nseindia.com/api/quote-derivative?symbol='+symbol)
        try:
            if(payload['error']=={}):
                print("Please use nse_eq() function to reduce latency.")
                payload = nsefetch('https://www.nseindia.com/api/quote-equity?symbol='+symbol)
        except KeyError:
            pass
    except (KeyError, NSEEndpointError):
        # /api/quote-derivative is likewise retired (confirmed HTTP 404 on
        # the live site). getSymbolDerivativesData via nse_quote_derivatives()
        # is the working replacement (different JSON shape: a flat 'data'
        # list of per-strike CE/PE records instead of records/underlyingValue).
        logging.warning(
            "nse_fno(%s): /api/quote-derivative is retired; returning data "
            "from the newer NextApi derivatives endpoint instead (see "
            "nse_quote_derivatives() - the JSON shape differs).",
            symbol,
        )
        payload = nse_quote_derivatives(symbol)
    return payload

def quote_equity(symbol):
    return nse_eq(symbol)

def quote_derivative(symbol):
    return nse_fno(symbol)

def option_chain(symbol):
    return nse_optionchain_scrapper(symbol)

def nse_holidays(type="trading"):
    # Round 3 bug fix: these were two independent `if`s with no `else`, so
    # any type other than exactly "trading"/"clearing" left `payload` never
    # assigned, and `return payload` blew up with an unrelated-looking
    # UnboundLocalError instead of a clear "invalid type" message. Confirmed
    # live that NSE's own /api/holiday-master endpoint only accepts these
    # two type values (anything else comes back HTTP 200 with a zero-length
    # body) -- so raise a clear, descriptive error for anything else.
    if(type=="clearing"):
        payload = nsefetch('https://www.nseindia.com/api/holiday-master?type=clearing')
    elif(type=="trading"):
        payload = nsefetch('https://www.nseindia.com/api/holiday-master?type=trading')
    else:
        raise ValueError(
            f"nse_holidays: invalid type={type!r} -- NSE's holiday-master "
            f"API only supports type='trading' or type='clearing'."
        )
    return payload

def holiday_master(type="trading"):
    return nse_holidays(type)

def nse_results(index="equities",period="Quarterly"):
    if(index=="equities") or (index=="debt") or (index=="sme"):
        if(period=="Quarterly") or (period=="Annual")or (period=="Half-Yearly")or (period=="Others"):
            payload = nsefetch('https://www.nseindia.com/api/corporates-financial-results?index='+index+'&period='+period)
            return pd.json_normalize(payload)
        else:
            print("Give Correct Period Input")
    else:
        print("Give Correct Index Input")

def nse_events():
    output = nsefetch('https://www.nseindia.com/api/event-calendar')
    return pd.json_normalize(output)

def nse_past_results(symbol):
    symbol = nsesymbolpurify(symbol)
    return nsefetch('https://www.nseindia.com/api/results-comparision?symbol='+symbol)

def expiry_list(symbol, type=""):
    logging.info("Getting Expiry List of: " + symbol)
    symbol = nsesymbolpurify(symbol)
    url = f'https://www.nseindia.com/api/NextApi/apiClient/GetQuoteApi?functionName=getOptionChainDropdown&symbol={symbol}'
    payload = nsefetch(url)
    
    if not payload or 'expiryDates' not in payload:
        return [] if type == "list" else pd.DataFrame()

    expiry_dates = payload['expiryDates']
    
    # Format dates from DD-MM-YYYY to DD-Mon-YYYY
    formatted_dates = []
    for d in expiry_dates:
        try:
            dt = datetime.datetime.strptime(d, "%d-%m-%Y")
            formatted_dates.append(dt.strftime("%d-%b-%Y"))
        except:
            formatted_dates.append(d)
    
    if type == "list":
        return formatted_dates
    else:
        # If anything other than "list" is provided (like "df", "pandas", or default), return DataFrame
        return pd.DataFrame({'Date': formatted_dates})


def nse_custom_function_secfno(symbol,attribute="lastPrice"):
    positions = nsefetch('https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O')
    endp = len(positions['data'])
    for x in range(0, endp):
        if(positions['data'][x]['symbol']==symbol.upper()):
            return positions['data'][x][attribute]

def nse_blockdeal():
    payload = nsefetch('https://nseindia.com/api/block-deal')
    return payload

def nse_marketStatus():
    payload = nsefetch('https://nseindia.com/api/marketStatus')
    return payload

def nse_circular(mode="latest"):
    # The old mode="latest" path (https://nseindia.com/api/latest-circular,
    # no `www.`) is dead on the live site: it returns HTTP 200 but a bare
    # {'error': True, 'status': 500} JSON body -- confirmed this is NOT an
    # Akamai bot-challenge (no injected script, no 403/503), just NSE's own
    # "this route doesn't exist" response. NSE renamed the circulars page
    # itself from /resources/circulars to
    # /resources/exchange-communication-circulars, and a Playwright network
    # capture on that live page shows it calling
    # https://www.nseindia.com/api/circulars?fromDate=DD-MM-YYYY&toDate=DD-MM-YYYY
    # (with `www.`) -- the SAME URL this function's own mode!="latest"
    # branch already used and which was independently confirmed live
    # (zero params defaults to NSE's own last-7-days/150-record window).
    # Fix: route "latest" to that same working endpoint too, instead of the
    # dead no-www path.
    if(mode=="latest"):
        payload = nsefetch('https://www.nseindia.com/api/circulars')
    else:
        payload = nsefetch('https://www.nseindia.com/api/circulars')
    return payload

def nse_fiidii(mode="pandas"):
    try:
        if(mode=="pandas"):
            return pd.DataFrame(nsefetch('https://www.nseindia.com/api/fiidiiTradeReact'))
        else:
            return nsefetch('https://www.nseindia.com/api/fiidiiTradeReact')
    except:
        logger.info("Pandas is not working for some reason.")
        return nsefetch('https://www.nseindia.com/api/fiidiiTradeReact')

def nsetools_get_quote(symbol):
    payload = nsefetch('https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O')
    for m in range(len(payload['data'])):
        if(payload['data'][m]['symbol']==symbol.upper()):
            return payload['data'][m]


def _nse_index_data():
    # iislliveblob.niftyindices.com is a dead host (confirmed live: NXDOMAIN,
    # twice). /api/allIndices on the main site carries the same live index
    # quotes (139 indices as of this writing, including pe/pb/dy per index).
    # Its per-row key is 'index' (e.g. "NIFTY 50"), not the old 'indexName' --
    # alias it so nse_get_index_list()/nse_get_index_quote() below (and any
    # external code doing the same lookup) keep working unchanged.
    payload = nsefetch("https://www.nseindia.com/api/allIndices")
    rows = payload.get("data", [])
    for row in rows:
        row.setdefault("indexName", row.get("index"))
    return rows


def nse_index():
    return pd.DataFrame(_nse_index_data())

def nse_get_index_list():
    return pd.DataFrame(_nse_index_data())["indexName"].tolist()

def nse_get_index_quote(index):
    for row in _nse_index_data():
        if row["indexName"] == index.upper():
            return row

def nse_get_advances_declines(mode="pandas"):
    try:
        if(mode=="pandas"):
            positions = nsefetch('https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O')
            return pd.DataFrame(positions['data'])
        else:
            return nsefetch('https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O')
    except:
        logger.info("Pandas is not working for some reason.")
        return nsefetch('https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O')

def nse_get_top_losers():
    positions = nsefetch('https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O')
    df = pd.DataFrame(positions['data'])
    df = df.sort_values(by="pChange")
    return df.head(5)

def nse_get_top_gainers():
    positions = nsefetch('https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O')
    df = pd.DataFrame(positions['data'])
    df = df.sort_values(by="pChange" , ascending = False)
    return df.head(5)

def nse_get_fno_lot_sizes(symbol="all",mode="list"):
    # github.com/aeron7/nsepythonserver issue #4 ("lot sizes not working"):
    # two stacked bugs, confirmed live. (1) archives.nseindia.com silently
    # redirects this specific file to an unrelated PDF circular these days
    # (NSE's archives -> nsearchives host migration left a stale redirect on
    # just this path) -- nsearchives.nseindia.com/content/fo/fo_mktlots.csv
    # is the real, current location, confirmed live with the exact same CSV
    # shape. (2) plain `requests.get()` against nsearchives.nseindia.com
    # hangs to a read-timeout (confirmed live) -- it needs the same
    # curl_cffi TLS impersonation as the rest of the site now.
    url="https://nsearchives.nseindia.com/content/fo/fo_mktlots.csv"

    if(mode=="list"):
        s = _nse_fetch_csv_text(url)
        res_dict = {}
        for line in s.split('\n'):
          if line != '' and re.search(',', line) and (line.casefold().find('symbol') == -1):
              (code, name) = [x.strip() for x in line.split(',')[1:3]]
              res_dict[code] = int(name)
        if(symbol=="all"):
            return res_dict
        if(symbol!=""):
            return res_dict[symbol.upper()]

    if(mode=="pandas"):
        payload = pd.read_csv(io.StringIO(_nse_fetch_csv_text(url)))
        if(symbol=="all"):
            return payload
        else:
            payload = payload[(payload.iloc[:, 1] == symbol.upper())]
            return payload

def whoistheboss():
    return "subhash"

def indiavix():
    payload = nsefetch("https://www.nseindia.com/api/allIndices")
    for x in range(0, len(payload["data"])):
        if(payload["data"][x]["index"]=="INDIA VIX"):
            return payload["data"][x]["last"]

def index_info(index):
    payload = nsefetch("https://www.nseindia.com/api/allIndices")
    for x in range(0, len(payload["data"])):
        if(payload["data"][x]["index"]==index):
            return payload["data"][x]

import math
from scipy.stats import norm

def black_scholes_dexter(S0,X,t,σ="",r=10,q=0.0,td=365):

  if(σ==""):σ =indiavix()

  S0,X,σ,r,q,t = float(S0),float(X),float(σ/100),float(r/100),float(q/100),float(t/td)
  #https://unofficed.com/black-scholes-model-options-calculator-google-sheet/

  # Round 3 bug fix: t=0 (an option literally expiring today, a completely
  # normal real-world input given NSE's weekly expiries) used to raise a
  # raw, uncaught ZeroDivisionError from sigma*sqrt(t) in d1's denominator.
  # This is a genuine math-domain limit of the Black-Scholes formula (it's
  # undefined at t=0), not an NSE-API issue -- so raise a clear, descriptive
  # error pointing the caller at intrinsic value instead of a bare
  # ZeroDivisionError.
  if t <= 0:
      raise ValueError(
          f"black_scholes_dexter: t={t*td:g} days to expiry must be > 0 -- "
          f"Black-Scholes delta/gamma/theta/vega are undefined at t=0 (an "
          f"option expiring today). Use intrinsic value "
          f"(max(S0-X,0) for a call / max(X-S0,0) for a put) directly "
          f"instead for a same-day expiry."
      )

  d1 = (math.log(S0/X)+(r-q+0.5*σ**2)*t)/(σ*math.sqrt(t))
  #stackoverflow.com/questions/34258537/python-typeerror-unsupported-operand-types-for-float-and-int

  #stackoverflow.com/questions/809362/how-to-calculate-cumulative-normal-distribution
  Nd1 = (math.exp((-d1**2)/2))/math.sqrt(2*math.pi)
  d2 = d1-σ*math.sqrt(t)
  Nd2 = norm.cdf(d2)
  call_theta =(-((S0*σ*math.exp(-q*t))/(2*math.sqrt(t))*(1/(math.sqrt(2*math.pi)))*math.exp(-(d1*d1)/2))-(r*X*math.exp(-r*t)*norm.cdf(d2))+(q*math.exp(-q*t)*S0*norm.cdf(d1)))/td
  put_theta =(-((S0*σ*math.exp(-q*t))/(2*math.sqrt(t))*(1/(math.sqrt(2*math.pi)))*math.exp(-(d1*d1)/2))+(r*X*math.exp(-r*t)*norm.cdf(-d2))-(q*math.exp(-q*t)*S0*norm.cdf(-d1)))/td
  call_premium =math.exp(-q*t)*S0*norm.cdf(d1)-X*math.exp(-r*t)*norm.cdf(d1-σ*math.sqrt(t))
  put_premium =X*math.exp(-r*t)*norm.cdf(-d2)-math.exp(-q*t)*S0*norm.cdf(-d1)
  call_delta =math.exp(-q*t)*norm.cdf(d1)
  put_delta =math.exp(-q*t)*(norm.cdf(d1)-1)
  gamma =(math.exp(-r*t)/(S0*σ*math.sqrt(t)))*(1/(math.sqrt(2*math.pi)))*math.exp(-(d1*d1)/2)
  vega = ((1/100)*S0*math.exp(-r*t)*math.sqrt(t))*(1/(math.sqrt(2*math.pi))*math.exp(-(d1*d1)/2))
  call_rho =(1/100)*X*t*math.exp(-r*t)*norm.cdf(d2)
  put_rho =(-1/100)*X*t*math.exp(-r*t)*norm.cdf(-d2)

  return call_theta,put_theta,call_premium,put_premium,call_delta,put_delta,gamma,vega,call_rho,put_rho

def equity_history_virgin(symbol,series,start_date,end_date):
    #url="https://www.nseindia.com/api/historical/cm/equity?symbol="+symbol+"&series=[%22"+series+"%22]&from="+str(start_date)+"&to="+str(end_date)+""
    # NOTE: the original /api/historical/cm/equity route is retired on the
    # live site (confirmed HTTP 503 as of 2026, even via curl_cffi). NSE's
    # replacement is /api/historicalOR/cm/equity -- same query params, same
    # response shape (payload['data'] records with CH_TIMESTAMP/
    # CH_CLOSING_PRICE/etc), confirmed live, so this is a plain host-path
    # swap with no downstream parsing changes needed.
    url = 'https://www.nseindia.com/api/historicalOR/cm/equity?symbol=' + symbol + '&series=["' + series + '"]&from=' + start_date + '&to=' + end_date

    payload = nsefetch(url)
    return pd.DataFrame.from_records(payload["data"])

# You shall see beautiful use the logger function.
def equity_history(symbol,series,start_date,end_date):
    #We are getting the input in text. So it is being converted to Datetime object from String.
    start_date = datetime.datetime.strptime(start_date, "%d-%m-%Y")
    end_date = datetime.datetime.strptime(end_date, "%d-%m-%Y")
    logging.info("Starting Date: "+str(start_date))
    logging.info("Ending Date: "+str(end_date))

    #We are calculating the difference between the days
    diff = end_date-start_date
    logging.info("Total Number of Days: "+str(diff.days))
    logging.info("Total FOR Loops in the program: "+str(int(diff.days/40)))
    logging.info("Remainder Loop: " + str(diff.days-(int(diff.days/40)*40)))


    total=pd.DataFrame()
    for i in range (0,int(diff.days/40)):

        temp_date = (start_date+datetime.timedelta(days=(40))).strftime("%d-%m-%Y")
        start_date = datetime.datetime.strftime(start_date, "%d-%m-%Y")

        logging.info("Loop = "+str(i))
        logging.info("====")
        logging.info("Starting Date: "+str(start_date))
        logging.info("Ending Date: "+str(temp_date))
        logging.info("====")

        #total=total.append(equity_history_virgin(symbol,series,start_date,temp_date))
        #total=total.concat(equity_history_virgin(symbol,series,start_date,temp_date))
        total = pd.concat([total, equity_history_virgin(symbol, series, start_date, temp_date)])


        logging.info("Length of the Table: "+ str(len(total)))

        #Preparation for the next loop
        start_date = datetime.datetime.strptime(temp_date, "%d-%m-%Y")


    start_date = datetime.datetime.strftime(start_date, "%d-%m-%Y")
    end_date = datetime.datetime.strftime(end_date, "%d-%m-%Y")

    logging.info("End Loop")
    logging.info("====")
    logging.info("Starting Date: "+str(start_date))
    logging.info("Ending Date: "+str(end_date))
    logging.info("====")

    #total=total.append(equity_history_virgin(symbol,series,start_date,end_date))
    #total=total.concat(equity_history_virgin(symbol,series,start_date,end_date))
    total = pd.concat([total, equity_history_virgin(symbol, series, start_date, end_date)])


    logging.info("Finale")
    logging.info("Length of the Total Dataset: "+ str(len(total)))
    payload = total.iloc[::-1].reset_index(drop=True)
    return payload

def derivative_history_virgin(symbol,start_date,end_date,instrumentType,expiry_date,strikePrice="",optionType=""):

    instrumentType = instrumentType.lower()

    if(instrumentType=="options"):
        instrumentType="OPTSTK"
        if("NIFTY" in symbol): instrumentType="OPTIDX"
        
    if(instrumentType=="futures"):
        instrumentType="FUTSTK"
        if("NIFTY" in symbol): instrumentType="FUTIDX"
        

    #if(((instrumentType=="OPTIDX")or (instrumentType=="OPTSTK")) and (expiry_date!="")):
    if(strikePrice!=""):
        strikePrice = "%.2f" % strikePrice
        strikePrice = str(strikePrice)

    # /api/historical/fo/derivatives is retired (HTTP 503 live); the
    # confirmed-working replacement is /api/historicalOR/fo/derivatives with
    # the same query params and response shape.
    nsefetch_url = "https://www.nseindia.com/api/historicalOR/fo/derivatives?&from="+str(start_date)+"&to="+str(end_date)+"&optionType="+optionType+"&strikePrice="+strikePrice+"&expiryDate="+expiry_date+"&instrumentType="+instrumentType+"&symbol="+symbol+""
    payload = nsefetch(nsefetch_url)
    logging.info(nsefetch_url)
    logging.info(payload)
    return pd.DataFrame.from_records(payload["data"])

def derivative_history(symbol,start_date,end_date,instrumentType,expiry_date,strikePrice="",optionType=""):
    #We are getting the input in text. So it is being converted to Datetime object from String.
    start_date = datetime.datetime.strptime(start_date, "%d-%m-%Y")
    end_date = datetime.datetime.strptime(end_date, "%d-%m-%Y")
    logging.info("Starting Date: "+str(start_date))
    logging.info("Ending Date: "+str(end_date))

    #We are calculating the difference between the days
    diff = end_date-start_date
    logging.info("Total Number of Days: "+str(diff.days))
    logging.info("Total FOR Loops in the program: "+str(int(diff.days/40)))
    logging.info("Remainder Loop: " + str(diff.days-(int(diff.days/40)*40)))


    total=pd.DataFrame()
    for i in range (0,int(diff.days/40)):

        temp_date = (start_date+datetime.timedelta(days=(40))).strftime("%d-%m-%Y")
        start_date = datetime.datetime.strftime(start_date, "%d-%m-%Y")

        logging.info("Loop = "+str(i))
        logging.info("====")
        logging.info("Starting Date: "+str(start_date))
        logging.info("Ending Date: "+str(temp_date))
        logging.info("====")

        #total=total.append(derivative_history_virgin(symbol,start_date,temp_date,instrumentType,expiry_date,strikePrice,optionType))
        #total=total.concat([total, derivative_history_virgin(symbol,start_date,temp_date,instrumentType,expiry_date,strikePrice,optionType)])
        total = pd.concat([total, derivative_history_virgin(symbol, start_date, temp_date, instrumentType, expiry_date, strikePrice, optionType)])


        logging.info("Length of the Table: "+ str(len(total)))

        #Preparation for the next loop
        start_date = datetime.datetime.strptime(temp_date, "%d-%m-%Y")


    start_date = datetime.datetime.strftime(start_date, "%d-%m-%Y")
    end_date = datetime.datetime.strftime(end_date, "%d-%m-%Y")

    logging.info("End Loop")
    logging.info("====")
    logging.info("Starting Date: "+str(start_date))
    logging.info("Ending Date: "+str(end_date))
    logging.info("====")

    #total=total.append(derivative_history_virgin(symbol,start_date,end_date,instrumentType,expiry_date,strikePrice,optionType))
    #total = total.concat([total, derivative_history_virgin(symbol,start_date,end_date,instrumentType,expiry_date,strikePrice,optionType)])
    total = pd.concat([total, derivative_history_virgin(symbol, start_date, end_date, instrumentType, expiry_date, strikePrice, optionType)])



    logging.info("Finale")
    logging.info("Length of the Total Dataset: "+ str(len(total)))
    payload = total.iloc[::-1].reset_index(drop=True)
    return payload


def expiry_history(symbol,start_date="",end_date="",type="options"):
    # Same retirement as derivative_history_virgin()/equity_history_virgin()
    # above -- /api/historical/* is gone, /api/historicalOR/* is the working
    # replacement with an identical response shape.
    nsefetch_url = "https://www.nseindia.com/api/historicalOR/fo/derivatives/meta?&from="+start_date+"&to="+end_date+"&symbol="+symbol+""
    payload = nsefetch(nsefetch_url)

    #print(payload)

    payload_data = None
    for key, value in payload['expiryDatesByInstrument'].items():
      if type.lower() == "options" and "OPT" in key:
          payload_data = payload['expiryDatesByInstrument'][key]
          break
      elif type.lower() == "futures" and "FUT" in key:
          payload_data =  payload['expiryDatesByInstrument'][key]
          break

    if payload_data is None:
        return []

    # Round 3 bug fix: calling this with its own documented defaults (no
    # dates -- expiry_history("NIFTY")) used to crash unconditionally with
    # `ValueError: time data '' does not match format '%d-%m-%Y'`, because
    # start_date/end_date default to "" but got passed straight into
    # strptime with no blank-check. Confirmed live that the endpoint itself
    # already handles blank from/to by returning the full unfiltered expiry
    # list -- so short-circuit and return that directly instead of crashing.
    if start_date == "" or end_date == "":
        return payload_data

    # Convert start_date and end_date to datetime objects
    start_date = datetime.datetime.strptime(start_date, "%d-%m-%Y")
    end_date = datetime.datetime.strptime(end_date, "%d-%m-%Y")

    # Initialize an empty list to store filtered dates
    filtered_date_payload = []

    # Initialize a flag to check if the first date after end_date has been added
    added_after_end_date = False

    # Iterate through date_payload and filter dates within the range
    for date_str in payload_data:
        date_obj = datetime.datetime.strptime(date_str, "%d-%b-%Y")
        if start_date <= date_obj <= end_date:
            filtered_date_payload.append(date_str)
        elif date_obj > end_date and not added_after_end_date:
            filtered_date_payload.append(date_str)
            added_after_end_date = True

    return filtered_date_payload

# # Nifty Indicies Site
#
# niftyindices.com is a completely separate host/site from nseindia.com (no
# Akamai Bot Manager symptoms observed here) -- but it was fully redesigned
# onto a different CMS at some point: the old ASP.NET WebMethods under
# `niftyindices.com/Backpage.aspx/*` (returning `{"d": "<json string>"}`) are
# gone, and POSTing to them now just returns the site's homepage HTML, which
# is exactly github.com/aeron7/nsepython issue #78's
# `JSONDecodeError: Expecting value: line 1 column 2 (char 1)`.
#
# The working replacement (confirmed live) is `www.niftyindices.com/BackPage/*`
# (note: `www.` + `BackPage` not `Backpage.aspx`), which wants a short session
# warm-up first (visiting the historical-data report page) and returns a
# direct JSON array rather than the old `{"d": "..."}` wrapper.

niftyindices_headers = {
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8',
    'Content-Type': 'application/json; charset=UTF-8',
    'Origin': 'https://www.niftyindices.com',
    'Referer': 'https://www.niftyindices.com/reports/historical-data',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest',
    'sec-ch-ua': '"Not;A=Brand";v="8", "Chromium";v="130", "Google Chrome";v="130"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

_niftyindices_session = None
_niftyindices_warmed = False


def _get_niftyindices_session():
    global _niftyindices_session, _niftyindices_warmed
    if _niftyindices_session is None:
        _niftyindices_session = requests.Session()
    if not _niftyindices_warmed:
        try:
            _niftyindices_session.get(
                "https://www.niftyindices.com/reports/historical-data",
                headers=niftyindices_headers, timeout=15,
            )
            _niftyindices_warmed = True
        except Exception as e:
            logging.warning("niftyindices.com session warm-up failed/partial: %s", e)
    return _niftyindices_session


def _niftyindices_fetch(endpoint, symbol, start_date, end_date):
    session = _get_niftyindices_session()
    data = {'cinfo': "{'name':'" + symbol + "','startDate':'" + start_date + "','endDate':'" + end_date + "','indexName':'" + symbol + "'}"}
    response = session.post(
        f"https://www.niftyindices.com/BackPage/{endpoint}",
        headers=niftyindices_headers, json=data, timeout=20,
    )
    text = response.text.strip()
    if text.startswith('<!DOCTYPE') or text.startswith('<html') or text == "":
        raise NSEEndpointError(
            f"niftyindices.com/BackPage/{endpoint} returned HTML/empty instead of JSON "
            f"(HTTP {response.status_code}) -- the site may be down or have changed again."
        )
    try:
        payload = response.json()
    except ValueError:
        raise NSEEndpointError(
            f"niftyindices.com/BackPage/{endpoint}: non-JSON body (HTTP {response.status_code})"
        )
    # Old API wrapped the payload as {"d": "<json string>"}; the new one
    # returns the array directly. Support both so this keeps working if
    # niftyindices.com ever reverts/mixes the two shapes.
    if isinstance(payload, dict) and "d" in payload:
        payload = json.loads(payload["d"])
    return pd.DataFrame.from_records(payload)


def index_history(symbol,start_date,end_date):
    return _niftyindices_fetch("getHistoricaldatatabletoString", symbol, start_date, end_date)

def index_pe_pb_div(symbol,start_date,end_date):
    return _niftyindices_fetch("getpepbHistoricaldataDBtoString", symbol, start_date, end_date)

def index_total_returns(symbol,start_date,end_date):
    return _niftyindices_fetch("getTotalReturnIndexString", symbol, start_date, end_date)

def get_bhavcopy(date):
    date = date.replace("-","")
    payload = pd.read_csv(io.StringIO(_nse_fetch_csv_text(
        "https://archives.nseindia.com/products/content/sec_bhavdata_full_"+date+".csv")))
    return payload

def get_bulkdeals():
    payload = pd.read_csv(io.StringIO(_nse_fetch_csv_text(
        "https://archives.nseindia.com/content/equities/bulk.csv")))
    return payload

def get_blockdeals():
    payload = pd.read_csv(io.StringIO(_nse_fetch_csv_text(
        "https://archives.nseindia.com/content/equities/block.csv")))
    return payload

def _nse_top_corp_info(symbol):
    """`/api/top-corp-info?symbol=X&market=equities` bundles a company's
    latest announcements, corporate actions (bonus/dividend/split/demerger),
    shareholding pattern history, financial results, and board meetings in
    one call -- confirmed live and working through curl_cffi+warm-up. This
    backs both dividend_timeline() and share_holding() below."""
    symbol = nsesymbolpurify(symbol)
    return nsefetch(f"https://www.nseindia.com/api/top-corp-info?symbol={symbol}&market=equities")


def dividend_timeline(symbol):
    """github.com/aeron7/nsepython issue #75: documented on
    unofficed.com/nse-python/ but never actually implemented in the code
    (calling it raised `AttributeError: module 'nsepython' has no attribute
    'dividend_timeline'`). Implemented here from `/api/top-corp-info`'s
    `corporate_actions` list, filtered down to the dividend-purpose entries
    (that list also contains bonuses/splits/demergers/etc, which this
    function intentionally excludes to match its name)."""
    data = _nse_top_corp_info(symbol)
    actions = (data.get("corporate_actions") or {}).get("data") or []
    dividends = [a for a in actions if "dividend" in (a.get("purpose") or "").lower()]
    return pd.DataFrame.from_records(dividends)


def share_holding(symbol):
    """github.com/aeron7/nsepython issue #75: same situation as
    dividend_timeline() above -- documented but not implemented. Built from
    `/api/top-corp-info`'s `shareholdings_patterns` data, which is a dict
    keyed by filing date (e.g. "31-Mar-2026") whose value is a list of
    {"<category>": "<percent>"} rows (Promoter & Promoter Group / Public /
    Shares held by Employee Trusts / Total). Flattened here into one row per
    filing date with a column per category, newest filing first."""
    data = _nse_top_corp_info(symbol)
    by_date = (data.get("shareholdings_patterns") or {}).get("data") or {}
    rows = []
    for filing_date, categories in by_date.items():
        row = {"date": filing_date}
        for entry in categories:
            for k, v in entry.items():
                row[k.strip()] = v.strip() if isinstance(v, str) else v
        rows.append(row)
    df = pd.DataFrame.from_records(rows)
    if not df.empty and "date" in df.columns:
        try:
            df = df.sort_values(
                by="date",
                key=lambda s: pd.to_datetime(s, format="%d-%b-%Y"),
                ascending=False,
            ).reset_index(drop=True)
        except Exception:
            pass
    return df


#Request from subhash
## https://unofficed.com/how-to-find-the-beta-of-indian-stocks-using-python/
def get_beta_df_maker(symbol,days):
    if("NIFTY" in symbol):
        end_date = datetime.datetime.now().strftime("%d-%b-%Y")
        end_date = str(end_date)

        start_date = (datetime.datetime.now()- datetime.timedelta(days=days)).strftime("%d-%b-%Y")
        start_date = str(start_date)

        df2=index_history(symbol,start_date,end_date)
        df2["daily_change"]=df2["CLOSE"].astype(float).pct_change()
        df2=df2[['HistoricalDate','daily_change']]
        df2 = df2.iloc[1: , :]
        return df2
    else:
        end_date = datetime.datetime.now().strftime("%d-%m-%Y")
        end_date = str(end_date)

        start_date = (datetime.datetime.now()- datetime.timedelta(days=days)).strftime("%d-%m-%Y")
        start_date = str(start_date)

        df = equity_history(symbol,"EQ",start_date,end_date)

        df["daily_change"]=df["CH_CLOSING_PRICE"].pct_change()
        df=df[['CH_TIMESTAMP','daily_change']]
        df = df.iloc[1: , :] #thispointer.com/drop-first-row-of-pandas-dataframe-3-ways/
        return df

def getbeta(symbol,days=365,symbol2="NIFTY 50"):
    return get_beta(symbol,days,symbol2)

def get_beta(symbol,days=365,symbol2="NIFTY 50"):
    #Default is 248 days. (Input of Subhash)
    # github.com/aeron7/nsepython issue #75: this used to raise a raw
    # KeyError('data') because equity_history() silently returned {} on a
    # blocked/retired endpoint. nsefetch() now raises a descriptive
    # NSEEndpointError instead of swallowing the failure -- surface that
    # (plus any other unexpected shape problem) as a clear, named error
    # instead of a bare KeyError, per the issue reporter's own suggestion.
    try:
        df = get_beta_df_maker(symbol,days)
        df2 = get_beta_df_maker(symbol2,days)
    except NSEEndpointError:
        raise
    except Exception as e:
        raise NSEEndpointError(
            f"get_beta({symbol!r}, symbol2={symbol2!r}): could not build the "
            f"daily-change series needed for beta -- {e}"
        ) from e

    x=df["daily_change"].tolist()
    y=df2["daily_change"].tolist()

    if not x or not y:
        raise NSEEndpointError(
            f"get_beta({symbol!r}, symbol2={symbol2!r}): got no historical "
            f"price data back for the requested {days}-day window."
        )

    #stackoverflow.com/questions/42670055/is-there-any-better-way-to-calculate-the-covariance-of-two-lists-than-this
    mean_x = sum(x) / len(x)
    mean_y = sum(y) / len(y)
    covariance = sum((a - mean_x) * (b - mean_y) for (a,b) in zip(x,y)) / len(x)

    mean = sum(y) / len(y)
    variance = sum((i - mean) ** 2 for i in y) / len(y)

    if variance == 0:
        raise NSEEndpointError(
            f"get_beta({symbol!r}, symbol2={symbol2!r}): symbol2 had zero "
            f"price variance over this window, beta is undefined."
        )

    beta = covariance/variance
    return round(beta,3)

def nse_preopen(key="NIFTY",type="pandas"):
    payload = nsefetch("https://www.nseindia.com/api/market-data-pre-open?key="+key+"")
    if(type=="pandas"):
        # NSE's pre-open-market window for most `key` values (e.g. "NIFTY")
        # is only populated for a few minutes each morning; outside that
        # window `data` is a legitimate empty list ({"data": [], "msg": "No
        # Data Found"}), which used to raise a confusing KeyError('metadata')
        # trying to pull a column out of an empty DataFrame. Return an empty
        # DataFrame instead.
        if not payload.get('data'):
            return pd.DataFrame()
        payload = pd.DataFrame(payload['data'])
        payload  = pd.json_normalize(payload['metadata'])
        return payload
    else:
        return payload

#By Avinash https://forum.unofficed.com/t/nsepython-documentation/376/102?u=dexter
def nse_preopen_movers(key="FO",filter=1.5):
    # Round 3 bug fix: the body hardcoded the literal 1.5/-1.5 thresholds
    # instead of using the `filter` parameter at all -- any caller passing
    # a custom threshold (nse_preopen_movers(key="FO", filter=50)) got
    # silently ignored and always got the same 1.5% cutoff back, with no
    # error or warning.
    preOpen_gainer=nse_preopen(key)
    return preOpen_gainer[preOpen_gainer['pChange'] >filter],preOpen_gainer[preOpen_gainer['pChange'] <-filter]

# type = "securities"
# type = "etf"
# type = "sme"
#
# sort = "volume"
# sort = "value"

def nse_most_active(type="securities",sort="value"):
    payload = nsefetch("https://www.nseindia.com/api/live-analysis-most-active-"+type+"?index="+sort+"")
    payload = pd.DataFrame(payload["data"])
    return payload


def nse_eq_symbols():
    #https://forum.unofficed.com/t/feature-request-stocklist-api/1073/11
    eq_list_pd = pd.read_csv(io.StringIO(_nse_fetch_csv_text(
        'https://archives.nseindia.com/content/equities/EQUITY_L.csv')))
    return eq_list_pd['SYMBOL'].tolist()

def nse_price_band_hitters(bandtype="both",view="AllSec"):
  payload = nsefetch("https://www.nseindia.com/api/live-analysis-price-band-hitter")
  
  #bandtype can be upper, lower, both
  #view can be AllSec,SecGtr20,SecLwr20
  return pd.DataFrame(payload[bandtype][view]["data"])

def nse_largedeals(mode="bulk_deals"):
  payload = nsefetch('https://www.nseindia.com/api/snapshot-capital-market-largedeal')
  if(mode=="bulk_deals"):
    return pd.DataFrame(payload["BULK_DEALS_DATA"])
  if(mode=="short_deals"):
    return pd.DataFrame(payload["SHORT_DEALS_DATA"])
  if(mode=="block_deals"):
    return pd.DataFrame(payload["BLOCK_DEALS_DATA"])

def nse_largedeals_historical(from_date, to_date, mode="bulk_deals"):
    # The old /api/historical/{bulk-deals,short-selling,block-deals} family is
    # retired on the live site (confirmed HTTP 503 straight from NSE's origin
    # -- not an Akamai bot-challenge: the 503 body is a tiny generic Apache
    # ErrorDocument page returned with a consistent ~20-30ms *origin* timing
    # on every single attempt, with or without warm-up/referer variations,
    # which is the signature of a dead backend route rather than a solvable
    # JS sensor wall).
    #
    # Found the real, current replacement by driving NSE's own "Bulk Deals/
    # Block Deals/ Short Selling Archives" report page
    # (https://www.nseindia.com/report-detail/display-bulk-and-block-deals)
    # with Playwright and capturing what it actually calls when you click
    # Go: `/api/historicalOR/bulk-block-short-deals?optionType=<mode>&from=
    # ..&to=..` -- same host-prefix swap pattern as equity/derivatives above,
    # just a different path and param name (`optionType=`, not a path
    # segment), confirmed live for all three modes. Response shape is the
    # same `{"data": [...]}` the old endpoint returned, just with a different
    # (current) NSE column-name scheme:
    #   bulk_deals/block_deals -> BD_DT_DATE, BD_DT_ORDER, BD_SYMBOL,
    #                              BD_SCRIP_NAME, BD_CLIENT_NAME, BD_BUY_SELL,
    #                              BD_QTY_TRD, BD_TP_WATP, BD_REMARKS
    #   short_deals            -> SS_DATE, SS_DATE_ORDER, SS_SYMBOL, SS_NAME,
    #                              SS_QTY
    if mode == "bulk_deals":
        option_type = "bulk_deals"
    elif mode == "short_deals":
        option_type = "short_selling"
    elif mode == "block_deals":
        option_type = "block_deals"
    else:
        option_type = mode

    url = ('https://www.nseindia.com/api/historicalOR/bulk-block-short-deals'
           '?optionType=' + option_type + '&from=' + from_date + '&to=' + to_date)
    logging.info("Fetching " + str(url))
    payload = nsefetch(url)
    return pd.DataFrame(payload["data"])

#https://forum.unofficed.com/t/feature-request-nse-fno-participant-wise-oi/1179/7
#print(get_fao_participant_oi("04-06-2021"))
def get_fao_participant_oi(date):
    date = date.replace("-","")
    # Round 3 bug fix: this CSV has a title/caption row as line 1
    # ('""Participant wise Open Interest...""') with the REAL header on
    # line 2 -- reading it with no skiprows made pandas parse the caption
    # as the header and shift the real header row down into the data,
    # mislabeling every single column (confirmed live on every trading date
    # tested: columns came out as 'Unnamed: 2', 'Unnamed: 3', etc instead of
    # 'Future Index Long', 'Total Short Contracts', ...).
    text = _nse_fetch_csv_text(
        "https://archives.nseindia.com/content/nsccl/fao_participant_oi_"+date+".csv")
    payload = pd.read_csv(io.StringIO(text), skiprows=1)
    # NSE's own header row carries stray trailing whitespace on a couple of
    # columns (e.g. "Future Stock Short       ") -- strip it so column
    # lookups by name work as documented.
    payload.columns = [c.strip() for c in payload.columns]
    return payload

#https://forum.unofficed.com/t/how-to-check-if-the-market-is-open-today-or-not/1268/1
def is_market_open(segment = "FO"): #COM,CD,CB,CMOT,COM,FO,IRD,MF,NDM,NTRP,SLBS
    # Bug fix: the previous version returned True/False based only on
    # holiday_json's *first* entry, so it almost always reported "open"
    # regardless of today's actual date (today is essentially never the
    # first holiday in the list). Scan the whole list for a match instead.
    holiday_json = nse_holidays()[segment]

    # Get today's date in the format 'dd-Mon-yyyy'
    today_date = datetime.date.today().strftime('%d-%b-%Y')

    for holiday in holiday_json:
        if holiday.get('tradingDate') == today_date:
            print(f"Market is closed today because of {holiday.get('description')}")
            return False

    print("FNO Market is open today. Have a Nice Trade!")
    return True

def nse_expirydetails_by_symbol(symbol,meta ="Futures",i=0):
    payload = nse_quote_derivatives(symbol)
    expiry_dates = []

    # Extract from new FNO payload structure
    if 'data' in payload:
        unique_dates = set()
        for entry in payload['data']:
            if 'expiryDate' in entry:
                # Filter by meta type if possible, though 'data' usually contains all
                # To be precise, we can check instrumentType
                it = entry.get('instrumentType', '')
                if (meta == "Futures" and "FUT" in it) or (meta == "Options" and "OPT" in it):
                    unique_dates.add(entry['expiryDate'])
        expiry_dates = sorted(list(unique_dates), key=lambda x: datetime.datetime.strptime(x, "%d-%b-%Y"))

    # Filter future dates
    future_expiry_dates = []
    if expiry_dates:
        temp_dates = [datetime.datetime.strptime(date, "%d-%b-%Y").date() for date in expiry_dates]
        future_expiry_dates = sorted([date.strftime("%d-%b-%Y") for date in temp_dates if date >= datetime.datetime.now().date()], key=lambda x: datetime.datetime.strptime(x, "%d-%b-%Y"))

    # Fallback to expiry_list if i is out of range
    if i >= len(future_expiry_dates):
        dates = expiry_list(symbol, type="list")
        if dates:
            temp_dates = [datetime.datetime.strptime(date, "%d-%b-%Y").date() for date in dates]
            future_expiry_dates = sorted([date.strftime("%d-%b-%Y") for date in temp_dates if date >= datetime.datetime.now().date()], key=lambda x: datetime.datetime.strptime(x, "%d-%b-%Y"))

    if i >= len(future_expiry_dates):
        return None, None

    currentExpiry = future_expiry_dates[i]
    currentExpiry_dt = datetime.datetime.strptime(currentExpiry, '%d-%b-%Y').date()
    date_today = run_time.date()
    dte = (currentExpiry_dt - date_today).days
    return currentExpiry_dt, dte

def security_wise_archive(from_date, to_date, symbol, series="ALL"):
    # The old /api/historical/securityArchives route is retired on the live
    # site (confirmed HTTP 503 straight from NSE's origin -- same dead-route
    # signature as nse_largedeals_historical() above, not a solvable Akamai
    # challenge: tiny generic Apache ErrorDocument body, consistent fast
    # origin timing on every attempt regardless of warm-up/referer).
    #
    # Found the real, current replacement by driving NSE's own "Security-wise
    # Archives (Equities)" report page
    # (https://www.nseindia.com/report-detail/eq_security) with Playwright
    # and capturing what it actually calls when you click Go:
    # `/api/historicalOR/generateSecurityWiseHistoricalData?from=..&to=..&
    # symbol=..&type=..&series=..` -- same host-prefix-swap family as
    # equity_history()/derivative_history() above, just a different path and
    # `type=` instead of `dataType=`. Confirmed live: response shape is the
    # same `{"data": [...]}` with the same CH_*/COP_DELIV_* column names the
    # old endpoint used (cross-checked against equity_history()'s numbers for
    # the same symbol/dates -- exact match).
    base_url = "https://www.nseindia.com/api/historicalOR/generateSecurityWiseHistoricalData"
    url = f"{base_url}?from={from_date}&to={to_date}&symbol={symbol.upper()}&type=priceVolumeDeliverable&series={series.upper()}"
    payload = nsefetch(url)
    return pd.DataFrame(payload['data'])


# ---------------------------------------------------------------------------
# NSE's official, no-auth MCP (Model Context Protocol) servers
#
# NSE India publishes its own free, no-API-key-required MCP servers
# (https://www.nseindia.com/nse-mcp) -- two streamable-HTTP endpoints:
#
#   "bhavcopy" -- https://mcp.nseindia.in/bhavcopy/cm/mcp
#       ("nse-bhavcopy-redis-mcp", 21 tools): historical/derived data --
#       stock & index history, valuations, corporate actions, comparisons,
#       moving averages, 52-week range, market mood/breadth, symbol search.
#
#   "cmmkt" -- https://mcp.nseindia.in/cmmkt/mcp
#       ("cm-market-mcp", 15 tools): live cash-market data -- live quotes,
#       gainers/losers, live index values, equity/SME/bond/call-auction
#       stock lists.
#
# This is a genuinely different, independent path into NSE data from the
# rest of this module: it is NSE's own hosted service, not a scrape of
# nseindia.com through curl_cffi's Akamai-impersonation transport, so it is
# unaffected by Akamai Bot Manager entirely and is often the more reliable
# choice when it covers the data you need. It still reuses this module's
# shared curl_cffi session (_get_nse_session()) purely for cheap connection
# pooling / one consistent TLS-fingerprint story -- the MCP calls themselves
# need no cookies, no warm-up, and no auth of any kind.
#
# Protocol notes (streamable-HTTP MCP, JSON-RPC 2.0):
#   - POST an "initialize" request first; the response carries a
#     "Mcp-Session-Id" (or "mcp-session-id") header that must be echoed back
#     as a header on every subsequent request for that session.
#   - A "notifications/initialized" notification should follow (no response
#     body expected) before calling any tool.
#   - "tools/call" responses come back either as plain JSON or as an
#     SSE-framed body (Content-Type: text/event-stream) shaped like
#     "event:message\ndata:{...}\n\n" -- both are handled below.
#   - The actual tool result is nested at result.content[0].text, which is
#     itself a JSON string in practice for every tool checked so far.
#   - A small number of tools (confirmed: nse_get_gainers / nse_get_losers
#     on the cmmkt server) currently come back with isError=false but an
#     inner {"error": "..."} payload -- a live bug on NSE's own server side
#     ("Failed to parse cached data: ArrayList cannot be cast to Map").
#     That is treated the same as any other failure here: raised as
#     NSEEndpointError rather than silently handed back as "data".
# ---------------------------------------------------------------------------

_NSE_MCP_SERVERS = {
    "bhavcopy": "https://mcp.nseindia.in/bhavcopy/cm/mcp",
    "cmmkt": "https://mcp.nseindia.in/cmmkt/mcp",
}

_NSE_MCP_CLIENT_VERSION = "2.98"

# Lightweight session-id cache, keyed by server URL, so repeated calls to the
# same MCP server don't re-run the "initialize" handshake every time.
_nse_mcp_session_cache = {}


def _nse_mcp_parse_response(r):
    """Parse one MCP HTTP response body, which comes back as either plain
    JSON or an SSE-framed body (Content-Type: text/event-stream) shaped like
    "event:message\\ndata:{...}\\n\\n". Returns the decoded JSON-RPC envelope
    dict either way.
    """
    ctype = r.headers.get("content-type", "") or ""
    if "text/event-stream" in ctype:
        data_lines = [
            line[len("data:"):].strip()
            for line in r.text.splitlines()
            if line.startswith("data:")
        ]
        if not data_lines:
            raise NSEEndpointError("nse_mcp: empty SSE response body")
        try:
            return json.loads("".join(data_lines))
        except ValueError:
            raise NSEEndpointError("nse_mcp: malformed SSE JSON payload")

    try:
        return r.json()
    except ValueError:
        # A server occasionally mislabels which framing it used -- scan for
        # "data:" lines regardless of the declared content-type before
        # giving up.
        data_lines = [
            line[len("data:"):].strip()
            for line in r.text.splitlines()
            if line.startswith("data:")
        ]
        if data_lines:
            try:
                return json.loads("".join(data_lines))
            except ValueError:
                pass
        raise NSEEndpointError(
            f"nse_mcp: non-JSON, non-SSE response body (content-type={ctype!r})"
        )


def _nse_mcp_initialize(server_url):
    """Run the MCP "initialize" handshake (+ "notifications/initialized")
    against server_url and return the Mcp-Session-Id NSE's server hands
    back (or "" if the server doesn't issue one). Retries up to 3 times --
    the bhavcopy endpoint has been observed to 502 on a cold first request.
    """
    session = _get_nse_session()
    mcp_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    init_body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "nsepython", "version": _NSE_MCP_CLIENT_VERSION},
        },
    }

    last_exc = None
    for attempt in range(3):
        try:
            r = session.post(server_url, headers=mcp_headers, json=init_body, timeout=30)
        except Exception as e:
            last_exc = NSEEndpointError(f"nse_mcp initialize: request failed for {server_url}: {e}")
            continue

        if r.status_code == 200:
            session_id = r.headers.get("mcp-session-id") or r.headers.get("Mcp-Session-Id") or ""
            notify_headers = dict(mcp_headers)
            if session_id:
                notify_headers["Mcp-Session-Id"] = session_id
            try:
                session.post(
                    server_url, headers=notify_headers,
                    json={"jsonrpc": "2.0", "method": "notifications/initialized"},
                    timeout=15,
                )
            except Exception:
                pass  # fire-and-forget notification; failure here is harmless
            return session_id

        last_exc = NSEEndpointError(
            f"nse_mcp initialize: HTTP {r.status_code} for {server_url}"
        )

    raise last_exc or NSEEndpointError(f"nse_mcp initialize: failed for {server_url}")


def _nse_mcp_get_session_id(server_url, force_new=False):
    """Return a cached Mcp-Session-Id for server_url, initializing (and
    caching) one if there isn't one yet or force_new is requested.
    """
    if not force_new and server_url in _nse_mcp_session_cache:
        return _nse_mcp_session_cache[server_url]
    session_id = _nse_mcp_initialize(server_url)
    _nse_mcp_session_cache[server_url] = session_id
    return session_id


def _nse_mcp_call(server_url, tool_name, arguments=None):
    """Call one tool on an NSE-official MCP server and return its parsed
    result payload.

    Handles the initialize/session-id handshake (with a small cache keyed
    by server_url so repeat calls don't re-initialize every time), both
    plain-JSON and SSE response framing, and the nested
    result.content[0].text tool-result convention (itself JSON-encoded for
    every tool checked so far). Raises NSEEndpointError -- never returns
    `{}` -- on any transport failure, JSON-RPC error, MCP tool-level error,
    or an application-level {"error": ...} payload the tool itself reports.
    """
    arguments = arguments or {}
    session = _get_nse_session()
    mcp_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }

    data = None
    last_exc = None
    for attempt in (1, 2):
        try:
            session_id = _nse_mcp_get_session_id(server_url, force_new=(attempt == 2))
        except NSEEndpointError as e:
            last_exc = e
            continue

        call_headers = dict(mcp_headers)
        if session_id:
            call_headers["Mcp-Session-Id"] = session_id

        body = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        try:
            r = session.post(server_url, headers=call_headers, json=body, timeout=30)
        except Exception as e:
            last_exc = NSEEndpointError(f"nse_mcp_call({tool_name}): request failed: {e}")
            continue

        if r.status_code in (401, 403, 404, 409, 502, 503) and attempt == 1:
            # Could be a stale/expired session id, or the transient 502 seen
            # on the bhavcopy endpoint's first request -- drop the cached
            # session and retry once with a fresh initialize.
            last_exc = NSEEndpointError(
                f"nse_mcp_call({tool_name}): HTTP {r.status_code} from {server_url}"
            )
            _nse_mcp_session_cache.pop(server_url, None)
            continue

        if r.status_code != 200:
            raise NSEEndpointError(
                f"nse_mcp_call({tool_name}): HTTP {r.status_code} from {server_url}"
            )

        data = _nse_mcp_parse_response(r)
        last_exc = None
        break

    if data is None:
        raise last_exc or NSEEndpointError(
            f"nse_mcp_call({tool_name}): failed against {server_url}"
        )

    if data.get("error"):
        raise NSEEndpointError(
            f"nse_mcp_call({tool_name}): JSON-RPC error: {data['error']}"
        )

    result = data.get("result") or {}
    content = result.get("content") or []
    if not content:
        raise NSEEndpointError(
            f"nse_mcp_call({tool_name}): empty/missing content in response: {result}"
        )

    text = content[0].get("text", "")
    try:
        payload = json.loads(text)
    except (ValueError, TypeError):
        payload = text  # plain text/markdown tool result -- hand it back as-is

    if result.get("isError"):
        raise NSEEndpointError(
            f"nse_mcp_call({tool_name}): tool reported an error: {payload}"
        )

    if isinstance(payload, dict) and "error" in payload:
        # Seen live on nse_get_gainers/nse_get_losers: isError=false but an
        # inner application-level error from NSE's own server. Don't hand
        # this back as if it were usable data.
        raise NSEEndpointError(
            f"nse_mcp_call({tool_name}): NSE's MCP server reported an application "
            f"error for this call: {payload['error']}"
        )

    return payload


def nse_mcp_call(server, tool_name, **kwargs):
    """Call ANY tool on NSE's own official, no-auth MCP servers by name --
    a generic escape hatch for a tool this module doesn't have a named
    wrapper for (yet), or any new tool NSE adds to either server in future.

    `server` is "bhavcopy" (historical/derived data) or "cmmkt" (live
    market data). `kwargs` become the tool's `arguments` object, passed
    straight through to NSE's MCP endpoint -- see nse_mcp_list_tools() for
    each tool's name, description and accepted arguments.

    Backed by NSE's own official, no-auth MCP server, not the
    Akamai-affected nseindia.com scrape path the rest of this module uses --
    a notably more reliable route when it covers the data you need.
    """
    server_url = _NSE_MCP_SERVERS.get(server)
    if server_url is None:
        raise NSEEndpointError(
            f"nse_mcp_call: unknown server {server!r}, expected 'bhavcopy' or 'cmmkt'"
        )
    return _nse_mcp_call(server_url, tool_name, kwargs)


def nse_mcp_list_tools(server=""):
    """Return NSE's own live tools/list response -- name, description and
    full inputSchema -- for one MCP server ("bhavcopy" or "cmmkt"), or both
    (as a dict keyed by server name) when `server` is omitted/empty.

    Always asks the server live rather than returning a hardcoded copy, so
    this stays accurate if/when NSE changes either server's toolset.
    """
    if server:
        if server not in _NSE_MCP_SERVERS:
            raise NSEEndpointError(
                f"nse_mcp_list_tools: unknown server {server!r}, expected 'bhavcopy' or 'cmmkt'"
            )
        servers = {server: _NSE_MCP_SERVERS[server]}
    else:
        servers = _NSE_MCP_SERVERS

    session = _get_nse_session()
    out = {}
    for name, url in servers.items():
        session_id = _nse_mcp_get_session_id(url)
        mcp_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if session_id:
            mcp_headers["Mcp-Session-Id"] = session_id
        body = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        r = session.post(url, headers=mcp_headers, json=body, timeout=30)
        if r.status_code != 200:
            raise NSEEndpointError(f"nse_mcp_list_tools({name}): HTTP {r.status_code}")
        data = _nse_mcp_parse_response(r)
        if data.get("error"):
            raise NSEEndpointError(f"nse_mcp_list_tools({name}): JSON-RPC error: {data['error']}")
        out[name] = (data.get("result") or {}).get("tools", [])

    return out[server] if server else out


def _nse_mcp_records(payload, key):
    """Return payload[key] (a list of record-dicts) as a DataFrame, or an
    empty DataFrame if the key is absent -- the same "list field on a dict
    payload becomes a DataFrame" convention used throughout this file.
    """
    rows = payload.get(key) if isinstance(payload, dict) else None
    return pd.DataFrame(rows if rows else [])


# ---------------------------------------------------------------------------
# Named wrappers -- "bhavcopy" server (nse-bhavcopy-redis-mcp, 21 tools)
# ---------------------------------------------------------------------------

def nse_mcp_get_top_by_volume(date="today", n=10, sort_by="volume"):
    """Get the top N most actively traded NSE stocks on a date, sorted by
    'volume' (traded quantity) or 'value' (turnover in Rs). Backed by NSE's
    own official no-auth MCP server (bhavcopy)."""
    payload = nse_mcp_call("bhavcopy", "get_top_by_volume", date=date, n=n, sortBy=sort_by)
    return _nse_mcp_records(payload, "stocks")


def nse_mcp_get_top_movers(date="today", n=10, direction="gain"):
    """Get the top N gaining ('gain') or losing ('loss') NSE stocks on a
    date, with OHLCV details. Backed by NSE's own official no-auth MCP
    server (bhavcopy)."""
    payload = nse_mcp_call("bhavcopy", "get_top_movers", date=date, n=n, direction=direction)
    return _nse_mcp_records(payload, "stocks")


def nse_mcp_nse_lookup_symbol(query):
    """Look up NSE ticker symbols by partial name or keyword (ticker list
    only, no price data). Backed by NSE's own official no-auth MCP server
    (bhavcopy)."""
    payload = nse_mcp_call("bhavcopy", "nse_lookup_symbol", query=query)
    return payload.get("symbols", []) if isinstance(payload, dict) else payload


def nse_mcp_get_market_mood(date="today"):
    """Get a factual read of NSE market mood for a day: India VIX level and
    trend, index/stock advance-decline breadth, and benchmark changes.
    Backed by NSE's own official no-auth MCP server (bhavcopy)."""
    return nse_mcp_call("bhavcopy", "get_market_mood", date=date)


def nse_mcp_get_index_valuation(index_name, months=24, date="today"):
    """Get an NSE index's valuation ratios (P/E, P/B, dividend yield) and
    where today's value sits within its own recent range. Backed by NSE's
    own official no-auth MCP server (bhavcopy)."""
    return nse_mcp_call(
        "bhavcopy", "get_index_valuation", indexName=index_name, months=months, date=date
    )


def nse_mcp_get_market_breadth(date="today"):
    """Get overall NSE market breadth for a trading date: advances,
    declines, unchanged, A/D ratio, total volume. Backed by NSE's own
    official no-auth MCP server (bhavcopy)."""
    return nse_mcp_call("bhavcopy", "get_market_breadth", date=date)


def nse_mcp_get_corporate_actions(symbol, from_date="", to_date=""):
    """Fetch actual NSE corporate action events (splits/bonus/dividends/
    other) for a stock, with exact ex-dates and adjustment factors. Backed
    by NSE's own official no-auth MCP server (bhavcopy)."""
    payload = nse_mcp_call(
        "bhavcopy", "get_corporate_actions", symbol=symbol, fromDate=from_date, toDate=to_date
    )
    return _nse_mcp_records(payload, "actions")


def nse_mcp_compare_indices(index_names, months=6, date="today"):
    """Compare 2 to 10 NSE indices side by side: return, annualised
    volatility, max drawdown and current valuation. Backed by NSE's own
    official no-auth MCP server (bhavcopy)."""
    payload = nse_mcp_call(
        "bhavcopy", "compare_indices", indexNames=index_names, months=months, date=date
    )
    return _nse_mcp_records(payload, "indices")


def nse_mcp_get_index_movers(date="today", period="1D", n=10, scope="equity"):
    """Get the top gaining and top losing NSE indices for a day or period
    (1D/1W/1M/3M/6M/1Y) -- useful for sector/theme rotation. Backed by NSE's
    own official no-auth MCP server (bhavcopy). Returns the raw dict (both
    a 'gainers' and a 'losers' list) since the result isn't a single table."""
    return nse_mcp_call(
        "bhavcopy", "get_index_movers", date=date, period=period, n=n, scope=scope
    )


def nse_mcp_get_ltp_by_date(symbol, date="today"):
    """Return the last traded (close) price for an NSE symbol on a date
    (previous trading day's price if the date is a non-trading day). Backed
    by NSE's own official no-auth MCP server (bhavcopy)."""
    return nse_mcp_call("bhavcopy", "get_ltp_by_date", symbol=symbol, date=date)


def nse_mcp_get_bulk_quote(symbols):
    """Get the latest price snapshot (OHLC, prev close, % change, volume)
    for up to 50 NSE stocks in one call. Backed by NSE's own official
    no-auth MCP server (bhavcopy)."""
    payload = nse_mcp_call("bhavcopy", "get_bulk_quote", symbols=symbols)
    return _nse_mcp_records(payload, "quotes")


def nse_mcp_get_volume_analysis(symbol, days=30):
    """Analyse trading volume trends for an NSE stock over N trading days:
    average/max/min volume, volume spike days, recent trend. Backed by
    NSE's own official no-auth MCP server (bhavcopy)."""
    return nse_mcp_call("bhavcopy", "get_volume_analysis", symbol=symbol, days=days)


def nse_mcp_get_stock_history(symbol, months=3, end_date="today"):
    """Get daily OHLCV price history for an NSE stock (up to 3 months per
    call; chain calls using the response's next_end_date for longer
    periods). Backed by NSE's own official no-auth MCP server (bhavcopy)."""
    payload = nse_mcp_call(
        "bhavcopy", "get_stock_history", symbol=symbol, months=months, endDate=end_date
    )
    return _nse_mcp_records(payload, "data")


def nse_mcp_get_index_snapshot(date="today", filter=""):
    """Get end-of-day values (OHLC, % change, turnover, P/E, P/B, dividend
    yield) for NSE indices on a date, optionally filtered by a name
    substring. Backed by NSE's own official no-auth MCP server (bhavcopy)."""
    payload = nse_mcp_call("bhavcopy", "get_index_snapshot", date=date, filter=filter)
    return _nse_mcp_records(payload, "indices")


def nse_mcp_search_symbols(query):
    """Search for NSE stock symbols by company name or partial symbol,
    returning matches with latest close price and % change. Backed by
    NSE's own official no-auth MCP server (bhavcopy)."""
    payload = nse_mcp_call("bhavcopy", "search_symbols", query=query)
    return _nse_mcp_records(payload, "results")


def nse_mcp_get_stock_vs_index(symbol, index_name="Nifty 50", months=12, date="today"):
    """Compare one NSE stock against a benchmark index over a period:
    return of each, outperformance, beta and correlation (stock return is
    already corporate-action adjusted). Backed by NSE's own official
    no-auth MCP server (bhavcopy)."""
    return nse_mcp_call(
        "bhavcopy", "get_stock_vs_index",
        symbol=symbol, indexName=index_name, months=months, date=date,
    )


def nse_mcp_compare_stocks(symbols, months=6):
    """Compare up to 10 NSE stocks side by side over a period: % return
    (ranked best to worst) and max drawdown per stock. Backed by NSE's own
    official no-auth MCP server (bhavcopy)."""
    payload = nse_mcp_call("bhavcopy", "compare_stocks", symbols=symbols, months=months)
    return _nse_mcp_records(payload, "stocks")


def nse_mcp_get_index_history(index_name, months=3, end_date="today"):
    """Get daily history (OHLC, % change, turnover, P/E, P/B, dividend
    yield) for an NSE index, up to 12 months per call; chain calls using
    next_end_date for longer periods. Backed by NSE's own official no-auth
    MCP server (bhavcopy)."""
    payload = nse_mcp_call(
        "bhavcopy", "get_index_history", indexName=index_name, months=months, endDate=end_date
    )
    return _nse_mcp_records(payload, "data")


def nse_mcp_moving_average(symbol, days=20):
    """Calculate the simple moving average (SMA) of close prices for an
    NSE stock over the last N trading days. Backed by NSE's own official
    no-auth MCP server (bhavcopy)."""
    return nse_mcp_call("bhavcopy", "moving_average", symbol=symbol, days=days)


def nse_mcp_get_52_week_high_low(symbol):
    """Get the 52-week high/low for an NSE stock, with dates and the
    current price's position within that range. Backed by NSE's own
    official no-auth MCP server (bhavcopy)."""
    return nse_mcp_call("bhavcopy", "get_52_week_high_low", symbol=symbol)


def nse_mcp_get_index_performance(index_name, date="today"):
    """Get an NSE index's price performance: 1-day change plus 1W/1M/3M/6M/
    1Y/2Y returns and 52-week high/low with distances. Backed by NSE's own
    official no-auth MCP server (bhavcopy)."""
    return nse_mcp_call("bhavcopy", "get_index_performance", indexName=index_name, date=date)


# ---------------------------------------------------------------------------
# Named wrappers -- "cmmkt" server (cm-market-mcp, 15 tools)
# ---------------------------------------------------------------------------

def nse_mcp_cm_get_live_market_data(index="gainers"):
    """Get live NSE market data for 'gainers' or 'loosers' (NSE's own
    spelling), refreshed every 5 minutes. Backed by NSE's own official
    no-auth MCP server (cmmkt)."""
    return nse_mcp_call("cmmkt", "cm_get_live_market_data", index=index)


def nse_mcp_cm_get_equity_stocks(limit=100, symbol_filter=""):
    """Get latest live data for NSE Capital Market EQUITY-segment stocks
    (series EQ/BE/BL/BT/IL/IQ), refreshed every minute. Backed by NSE's own
    official no-auth MCP server (cmmkt)."""
    payload = nse_mcp_call(
        "cmmkt", "cm_get_equity_stocks", limit=limit, symbolFilter=symbol_filter
    )
    return _nse_mcp_records(payload, "stocks")


def nse_mcp_nse_get_losers(limit=10):
    """Get the top N NSE stocks by % loss, flattened across all indices and
    sorted ascending. Backed by NSE's own official no-auth MCP server
    (cmmkt). NOTE: as of this writing NSE's own server has a live bug on
    this specific tool (confirmed: an internal "ArrayList cannot be cast to
    Map" exception) -- this raises NSEEndpointError until NSE fixes it; use
    nse_mcp_nse_get_market_movers() for the same ranking in the meantime."""
    payload = nse_mcp_call("cmmkt", "nse_get_losers", limit=limit)
    return _nse_mcp_records(payload, "losers") if isinstance(payload, dict) else payload


def nse_mcp_cm_get_call_auction_stocks(limit=100, symbol_filter=""):
    """Get latest live data for NSE Call Auction session stocks (series
    CA/CB), refreshed every minute. Backed by NSE's own official no-auth
    MCP server (cmmkt)."""
    payload = nse_mcp_call(
        "cmmkt", "cm_get_call_auction_stocks", limit=limit, symbolFilter=symbol_filter
    )
    return _nse_mcp_records(payload, "stocks")


def nse_mcp_cm_get_bond_stocks(limit=100, symbol_filter=""):
    """Get latest live data for NSE BONDS/debt instrument series, refreshed
    every minute. Backed by NSE's own official no-auth MCP server (cmmkt)."""
    payload = nse_mcp_call(
        "cmmkt", "cm_get_bond_stocks", limit=limit, symbolFilter=symbol_filter
    )
    return _nse_mcp_records(payload, "stocks")


def nse_mcp_cm_get_live_gainers():
    """Return raw NSE gainers data grouped by index segment (NIFTY,
    BANKNIFTY, NIFTYNEXT50, allSec, etc.) -- not sorted by % change; use
    nse_mcp_nse_get_market_movers() for a sorted ranking instead. Backed by
    NSE's own official no-auth MCP server (cmmkt)."""
    return nse_mcp_call("cmmkt", "cm_get_live_gainers")


def nse_mcp_nse_get_gainers(limit=10):
    """Get the top N NSE stocks by % gain, flattened across all indices and
    sorted descending. Backed by NSE's own official no-auth MCP server
    (cmmkt). NOTE: as of this writing NSE's own server has a live bug on
    this specific tool (confirmed: an internal "ArrayList cannot be cast to
    Map" exception) -- this raises NSEEndpointError until NSE fixes it; use
    nse_mcp_nse_get_market_movers() for the same ranking in the meantime."""
    payload = nse_mcp_call("cmmkt", "nse_get_gainers", limit=limit)
    return _nse_mcp_records(payload, "gainers") if isinstance(payload, dict) else payload


def nse_mcp_cm_get_data_status():
    """Check freshness of NSE live gainers/losers market data (last crawl
    time, crawl interval, Redis TTL). Backed by NSE's own official no-auth
    MCP server (cmmkt)."""
    return nse_mcp_call("cmmkt", "cm_get_data_status")


def nse_mcp_cm_get_stock_quote(symbol):
    """Get the latest live quote for one NSE CM stock by exact symbol
    (works for equity, SME, bond or call-auction segments). Backed by
    NSE's own official no-auth MCP server (cmmkt)."""
    return nse_mcp_call("cmmkt", "cm_get_stock_quote", symbol=symbol)


def nse_mcp_cm_get_index_quote(index_name):
    """Get the full live quote for one NSE index by exact name: last
    value, change, day's OHLC, 52-week range, and 1W/1M/1Y comparisons.
    Backed by NSE's own official no-auth MCP server (cmmkt)."""
    return nse_mcp_call("cmmkt", "cm_get_index_quote", indexName=index_name)


def nse_mcp_cm_get_sme_stocks(limit=100, symbol_filter=""):
    """Get latest live data for NSE SME (Small & Medium Enterprises) stocks
    (series SM/ST), refreshed every minute. Backed by NSE's own official
    no-auth MCP server (cmmkt)."""
    payload = nse_mcp_call(
        "cmmkt", "cm_get_sme_stocks", limit=limit, symbolFilter=symbol_filter
    )
    return _nse_mcp_records(payload, "stocks")


def nse_mcp_cm_get_live_losers():
    """Return raw NSE losers data grouped by index segment (NIFTY,
    BANKNIFTY, NIFTYNEXT50, allSec, etc.) -- not sorted by % change; use
    nse_mcp_nse_get_market_movers() for a sorted ranking instead. Backed by
    NSE's own official no-auth MCP server (cmmkt)."""
    return nse_mcp_call("cmmkt", "cm_get_live_losers")


def nse_mcp_cm_get_live_indices(group="", name_filter=""):
    """Get the latest live values of NSE indices (last, previous close,
    change, day's OHLC) across six groups (derivatives/broad/sectoral/
    strategy/thematic/fixed_income), optionally filtered by group and/or a
    name substring. Backed by NSE's own official no-auth MCP server
    (cmmkt)."""
    return nse_mcp_call("cmmkt", "cm_get_live_indices", group=group, nameFilter=name_filter)


def nse_mcp_nse_get_market_movers(index_name=None, limit=10):
    """Get the top N gainers and top N losers (sorted) from all NSE
    securities, or filtered to one of NIFTY/BANKNIFTY/NIFTYNEXT50. The
    PRIMARY tool for "top gainers/losers today" style questions. Backed by
    NSE's own official no-auth MCP server (cmmkt). Returns the raw dict
    (both a 'gainers' and a 'losers' list) since the result isn't a single
    table."""
    return nse_mcp_call(
        "cmmkt", "nse_get_market_movers", indexName=index_name or "", limit=limit
    )


def nse_mcp_cm_get_allstocks_status():
    """Check freshness of NSE's all-stocks live data cache: last crawl
    time, availability, and segment-wise stock counts. Backed by NSE's own
    official no-auth MCP server (cmmkt)."""
    return nse_mcp_call("cmmkt", "cm_get_allstocks_status")
