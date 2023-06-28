import json
import logging
import re
from datetime import date, datetime
from typing import Any, Union

import pandas as pd
import requests

from .constants import (
    HEADERS,
    INDICES,
    NSE_LIST,
)
from .urls import (
    BLOCK_DEAL_URL,
    CIRCULARS_URL,
    EVENT_CALENDAR_URL,
    FIIDII_TRADE_REACT_URL,
    HOLIDAY_MASTER_TYPE_CLEARING_URL,
    HOLIDAY_MASTER_TYPE_TRADING_URL,
    LATEST_CIRCULAR_URL,
    MARKET_STATUS_URL,
    OPTION_CHAIN_EQUITIES_URL,
    OPTION_CHAIN_INDICES_URL,
    POSITIONS_URL,
    QUOTE_DERIVATIVE_URL,
    QUOTE_EQUITY_URL,
    RESULTS_COMPARISION_URL,
)

mode = "local"

if mode == "local":

    def nsefetch(url: str) -> dict:
        return requests.get(url=url, headers=HEADERS).json()


run_time = datetime.now()


def running_status() -> bool:
    start_now = run_time.replace(hour=9, minute=15, second=0, microsecond=0)
    end_now = run_time.replace(hour=15, minute=30, second=0, microsecond=0)
    return start_now < run_time < end_now


def fnolist() -> list[str]:
    # df = pd.read_csv("https://www1.nseindia.com/content/fo/fo_mktlots.csv")
    # return [x.strip(' ') for x in df.drop(df.index[3]).iloc[:,1].to_list()]
    positions = nsefetch(url=POSITIONS_URL)
    return NSE_LIST + [
        positions["data"][i]["symbol"] for i in range(len(positions["data"]))
    ]


def nsesymbolpurify(symbol: str) -> str:
    return symbol.replace("&", "%26")  # URL Parse for Stocks Like M&M Finance


def nse_optionchain_scrapper(symbol: str) -> dict:
    symbol = nsesymbolpurify(symbol=symbol)
    url = (
        OPTION_CHAIN_INDICES_URL + symbol
        if any(x in symbol for x in INDICES)
        else OPTION_CHAIN_EQUITIES_URL + symbol
    )
    return nsefetch(url=url)


# TODO: implement this
def oi_chain_builder(symbol: str, expiry: str = "latest", oi_mode: str = "full"):
    pass


def nse_quote(symbol: str, section: str = "") -> dict:
    # https://forum.unofficed.com/t/nsetools-get-quote-is-not-fetching-delivery-data-and-delivery-can-you-include-this-as-part-of-feature-request/1115/4
    symbol = nsesymbolpurify(symbol=symbol)

    if not section:  # section == "" (empty string)
        url = (
            QUOTE_DERIVATIVE_URL + symbol
            if any(x in symbol for x in fnolist())
            else QUOTE_EQUITY_URL + symbol
        )
    else:
        url = QUOTE_EQUITY_URL + symbol + "&section=" + section

    return nsefetch(url=url)


def nse_expirydetails(payload: dict, i: int = 0) -> tuple[date, int]:
    current_expiry = datetime.strptime(
        payload["records"]["expiryDates"][i],
        "%d-%b-%Y",
    ).date()
    date_today = run_time.date()
    days_difference = (current_expiry - date_today).days
    return current_expiry, days_difference


def pcr(payload: dict, inp: str = "0") -> float:
    ce_oi = 0
    pe_oi = 0
    for data in payload["records"]["data"]:
        if data["expiryDate"] == payload["records"]["expiryDates"][inp]:
            try:
                ce_oi += data["CE"]["openInterest"]
                pe_oi += data["PE"]["openInterest"]
            except KeyError:
                pass
    return pe_oi / ce_oi


# TODO: implement this
def nse_quote_ltp(
    symbol: str,
    expiry_date: str = "latest",
    option_type: str = "-",
    strike_price: str = 0,
) -> dict[str, Any]:
    pass


# TODO: implement this
def nse_quote_meta(
    symbol: str,
    expiry_date: str = "latest",
    option_type: str = "-",
    strike_price: str = 0,
) -> dict[str, Any]:
    pass


def nse_optionchain_ltp(
    payload: dict,
    strike_price: str,
    option_type: str,
    inp: int = 0,
    intent: str = "",
) -> Union[float, None]:
    expiry_date = payload["records"]["expiryDates"][inp]
    for data in payload["records"]["data"]:
        if (data["strikePrice"] == strike_price) and (
            data["expiryDate"] == expiry_date
        ):
            if not intent:  # intent == "" (empty string)
                return data[option_type]["lastPrice"]
            elif intent == "sell":
                return data[option_type]["bidprice"]
            elif intent == "buy":
                return data[option_type]["askPrice"]
            else:
                return None
        else:
            return None


def nse_eq(symbol: str) -> dict:
    symbol = nsesymbolpurify(symbol=symbol)
    try:
        payload = nsefetch(url=QUOTE_EQUITY_URL + symbol)
        if "error" in payload and not payload["error"]:
            print("Please use nse_fno() function to reduce latency.")
            payload = nsefetch(url=QUOTE_DERIVATIVE_URL + symbol)
    except KeyError:
        print("Getting Error While Fetching.")
    return payload


def nse_fno(symbol: str) -> dict:
    symbol = nsesymbolpurify(symbol=symbol)
    try:
        payload = nsefetch(url=QUOTE_DERIVATIVE_URL + symbol)
        if "error" in payload and not payload["error"]:
            print("Please use nse_eq() function to reduce latency.")
            payload = nsefetch(url=QUOTE_EQUITY_URL + symbol)
    except KeyError:
        print("Getting Error While Fetching.")
    return payload


def quote_equity(symbol: str) -> dict:
    return nse_eq(symbol=symbol)


def quote_derivative(symbol: str) -> dict:
    return nse_fno(symbol=symbol)


def option_chain(symbol: str) -> dict:
    return nse_optionchain_scrapper(symbol=symbol)


def nse_holidays(type: str = "trading") -> dict:
    return (
        nsefetch(url=HOLIDAY_MASTER_TYPE_CLEARING_URL)
        if type == "clearing"
        else nsefetch(url=HOLIDAY_MASTER_TYPE_TRADING_URL)
    )


def holiday_master(type: str = "trading") -> dict:
    return nse_holidays(type=type)


# TODO: implement this
def nse_results(index: str = "equities", period: str = "Quarterly") -> None:
    pass


def nse_events() -> pd.DataFrame:
    output = nsefetch(url=EVENT_CALENDAR_URL)
    return pd.json_normalize(output)


def nse_past_results(symbol: str) -> dict:
    symbol = nsesymbolpurify(symbol=symbol)
    return nsefetch(url=RESULTS_COMPARISION_URL + symbol)


def expiry_list(symbol: str, type: str = "list") -> Union[pd.DataFrame, list]:
    logging.info(msg=f"Getting Expiry List of: {symbol}")

    if type == "list":
        payload = nse_quote(symbol=symbol)
        dates = list(set(payload["expiryDates"]))
        dates.sort(key=lambda date: datetime.strptime(date, "%d-%b-%Y"))
        return dates
    else:
        payload = nse_optionchain_scrapper(symbol=symbol)
        return pd.DataFrame({"Date": payload["records"]["expiryDates"]})


def nse_custom_function_secfno(symbol: str, attribute: str = "lastPrice") -> float:
    positions = nsefetch(url=POSITIONS_URL)
    for data in positions["data"]:
        if data["symbol"] == symbol.upper():
            return data[attribute]


def nse_blockdeal() -> dict:
    return nsefetch(url=BLOCK_DEAL_URL)


def nse_marketStatus() -> dict:
    return nsefetch(url=MARKET_STATUS_URL)


def nse_circular(mode: str = "latest") -> dict:
    return (
        nsefetch(url=LATEST_CIRCULAR_URL)
        if mode == "latest"
        else nsefetch(url=CIRCULARS_URL)
    )


def nse_fiidii(mode: str = "pandas") -> Union[pd.DataFrame, dict]:
    try:
        if mode == "pandas":
            return pd.DataFrame(nsefetch(url=FIIDII_TRADE_REACT_URL))
        else:
            return nsefetch(url=FIIDII_TRADE_REACT_URL)
    except Exception as e:
        logging.info(msg=str(e))
        logging.info(msg="Pandas is not working for some reason.")
        return nsefetch(url=FIIDII_TRADE_REACT_URL)
