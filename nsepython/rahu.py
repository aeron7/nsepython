import json
import logging
import math
import re
from datetime import date, datetime, timedelta
from typing import Any, Union

import pandas as pd
import requests
from constants import (
    COMPACT_OI_MODE_COLUMN_NAMES,
    FULL_OI_MODE_COLUMN_NAMES,
    HEADERS,
    INDICES,
    NIFTY_INDICIES_HEADERS,
    NSE_LIST,
)
from scipy.stats import norm
from urls import (
    ALL_INDICIES_URL,
    BLOCK_DEAL_URL,
    BLOCK_DEALS_URL,
    BULK_DEALS_URL,
    CIRCULARS_URL,
    CORPORATES_FINANCIAL_RESULTS_URL,
    EQUITY_LIST_URL,
    EVENT_CALENDAR_URL,
    FIIDII_TRADE_REACT_URL,
    FO_MARKET_LOTS_URL,
    GET_HISTORICAL_DATA_TABLE_TO_STRING_URL,
    GET_PE_PB_HISTORICAL_DATA_DB_TO_STRING_URL,
    GET_TOTAL_RETURN_INDEX_STRING_URL,
    HISTORICAL_DERIVATIVES_META_URL,
    HISTORICAL_DERIVATIVES_URL,
    HISTORICAL_EQUITY_URL,
    HOLIDAY_MASTER_TYPE_CLEARING_URL,
    HOLIDAY_MASTER_TYPE_TRADING_URL,
    LATEST_CIRCULAR_URL,
    LIVE_ANALYSIS_MOST_ACTIVE_URL,
    LIVE_INDICIES_WATCH_URL,
    MARKET_DATA_PRE_OPEN_URL,
    MARKET_STATUS_URL,
    OPTION_CHAIN_EQUITIES_URL,
    OPTION_CHAIN_INDICES_URL,
    POSITIONS_URL,
    QUOTE_DERIVATIVE_URL,
    QUOTE_EQUITY_URL,
    RESULTS_COMPARISION_URL,
    SEC_BHAV_DATA_FULL_URL,
)

run_time = datetime.now()

mode = "local"

if mode == "local":

    def nsefetch(url: str) -> dict:
        return requests.get(url=url, headers=HEADERS).json()


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


def oi_chain_builder(
    symbol: str,
    expiry: str = "latest",
    oi_mode: str = "full",
) -> tuple:
    payload = nse_optionchain_scrapper(symbol=symbol)

    column_names = (
        COMPACT_OI_MODE_COLUMN_NAMES
        if oi_mode == "compact"
        else FULL_OI_MODE_COLUMN_NAMES
    )

    oi_data = pd.DataFrame(columns=column_names)
    oi_row = {
        "CALLS_OI": 0,
        "CALLS_Chng in OI": 0,
        "CALLS_Volume": 0,
        "CALLS_IV": 0,
        "CALLS_LTP": 0,
        "CALLS_Net Chng": 0,
        "CALLS_Bid Qty": 0,
        "CALLS_Bid Price": 0,
        "CALLS_Ask Price": 0,
        "CALLS_Ask Qty": 0,
        "Strike Price": 0,
        "PUTS_OI": 0,
        "PUTS_Chng in OI": 0,
        "PUTS_Volume": 0,
        "PUTS_IV": 0,
        "PUTS_LTP": 0,
        "PUTS_Net Chng": 0,
        "PUTS_Bid Qty": 0,
        "PUTS_Bid Price": 0,
        "PUTS_Ask Price": 0,
        "PUTS_Ask Qty": 0,
    }

    if expiry == "latest":
        expiry = payload["records"]["expiryDates"][0]

    payload_data = payload["records"]["data"]
    for data in payload_data:
        if data["expiryDate"] == expiry:
            # TODO: why is this condition (1>0) being used??
            if 1 > 0:
                try:
                    data_ce = data["CE"]
                    oi_row["CALLS_OI"] = data_ce["openInterest"]
                    oi_row["CALLS_Chng in OI"] = data_ce["changeinOpenInterest"]
                    oi_row["CALLS_Volume"] = data_ce["totalTradedVolume"]
                    oi_row["CALLS_IV"] = data_ce["impliedVolatility"]
                    oi_row["CALLS_LTP"] = data_ce["lastPrice"]
                    oi_row["CALLS_Net Chng"] = data_ce["change"]
                    if oi_mode == "full":
                        oi_row["CALLS_Bid Qty"] = data_ce["bidQty"]
                        oi_row["CALLS_Bid Price"] = data_ce["bidprice"]
                        oi_row["CALLS_Ask Price"] = data_ce["askPrice"]
                        oi_row["CALLS_Ask Qty"] = data_ce["askQty"]
                except KeyError:
                    oi_row["CALLS_OI"] = 0
                    oi_row["CALLS_Chng in OI"] = 0
                    oi_row["CALLS_Volume"] = 0
                    oi_row["CALLS_IV"] = 0
                    oi_row["CALLS_LTP"] = 0
                    oi_row["CALLS_Net Chng"] = 0
                    if oi_mode == "full":
                        oi_row["CALLS_Bid Qty"] = 0
                        oi_row["CALLS_Bid Price"] = 0
                        oi_row["CALLS_Ask Price"] = 0
                        oi_row["CALLS_Ask Qty"] = 0

                oi_row["Strike Price"] = data["strikePrice"]

                try:
                    data_pe = data["PE"]
                    oi_row["PUTS_OI"] = data_pe["openInterest"]
                    oi_row["PUTS_Chng in OI"] = data_pe["changeinOpenInterest"]
                    oi_row["PUTS_Volume"] = data_pe["totalTradedVolume"]
                    oi_row["PUTS_IV"] = data_pe["impliedVolatility"]
                    oi_row["PUTS_LTP"] = data_pe["lastPrice"]
                    oi_row["PUTS_Net Chng"] = data_pe["change"]
                    if oi_mode == "full":
                        oi_row["PUTS_Bid Qty"] = data_pe["bidQty"]
                        oi_row["PUTS_Bid Price"] = data_pe["bidprice"]
                        oi_row["PUTS_Ask Price"] = data_pe["askPrice"]
                        oi_row["PUTS_Ask Qty"] = data_pe["askQty"]
                except KeyError:
                    oi_row["PUTS_OI"] = 0
                    oi_row["PUTS_Chng in OI"] = 0
                    oi_row["PUTS_Volume"] = 0
                    oi_row["PUTS_IV"] = 0
                    oi_row["PUTS_LTP"] = 0
                    oi_row["PUTS_Net Chng"] = 0
                    if oi_mode == "full":
                        oi_row["PUTS_Bid Qty"] = 0
                        oi_row["PUTS_Bid Price"] = 0
                        oi_row["PUTS_Ask Price"] = 0
                        oi_row["PUTS_Ask Qty"] = 0

            if oi_mode == "full":
                oi_row["CALLS_Chart"] = 0
                oi_row["PUTS_Chart"] = 0
            oi_data = pd.concat([oi_data, pd.DataFrame([oi_row])], ignore_index=True)
            oi_data["time_stamp"] = payload["records"]["timestamp"]
    return (
        oi_data,
        float(payload["records"]["underlyingValue"]),
        payload["records"]["timestamp"],
    )


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


def nse_quote_ltp(
    symbol: str,
    expiryDate: str = "latest",
    optionType: str = "-",
    strikePrice: str = 0,
) -> dict[str, Any]:
    payload = nse_quote(symbol=symbol)
    # https://stackoverflow.com/questions/7961363/removing-duplicates-in-lists
    # https://stackoverflow.com/questions/19199984/sort-a-list-in-python

    # BankNIFTY and NIFTY has weekly options. Using this Jugaad which has primary base of assumption that Reliance will not step out of FNO.
    # forum.unofficed.com/t/unable-to-find-nse-quote-meta-api/702/4
    if (symbol in INDICES) and (optionType == "Fut"):
        dates = expiry_list(symbol="RELIANCE", type="list")
        if expiryDate == "latest":
            expiryDate = dates[0]
        elif expiryDate == "next":
            expiryDate = dates[1]

    if (expiryDate == "latest") or (expiryDate == "next"):
        dates = list(set((payload["expiryDates"])))
        dates.sort(key=lambda date: datetime.strptime(date, "%d-%b-%Y"))
        if expiryDate == "latest":
            expiryDate = dates[0]
        elif expiryDate == "next":
            expiryDate = dates[1]

    meta = "Options"
    if optionType == "Fut":
        meta = "Futures"
    elif optionType == "PE":
        optionType = "Put"
    elif optionType == "CE":
        optionType = "Call"

    if optionType != "-":
        for stock in payload["stocks"]:
            stock_meta_data = stock["metadata"]
            if meta in stock_meta_data["instrumentType"]:
                if optionType == "Fut" and stock_meta_data["expiryDate"] == expiryDate:
                    lastPrice = stock_meta_data["lastPrice"]
                elif (
                    (optionType in ["Put", "Call"])
                    and stock_meta_data["expiryDate"] == expiryDate
                    and stock_meta_data["optionType"] == optionType
                    and stock_meta_data["strikePrice"] == strikePrice
                ):
                    lastPrice = stock_meta_data["lastPrice"]
    else:
        lastPrice = payload["underlyingValue"]

    return lastPrice


def nse_quote_meta(
    symbol: str,
    expiryDate: str = "latest",
    optionType: str = "-",
    strikePrice: str = 0,
) -> dict[str, Any]:
    payload = nse_quote(symbol=symbol)
    # https://stackoverflow.com/questions/7961363/removing-duplicates-in-lists
    # https://stackoverflow.com/questions/19199984/sort-a-list-in-python

    # BankNIFTY and NIFTY has weekly options. Using this Jugaad which has primary base of assumption that Reliance will not step out of FNO.
    # forum.unofficed.com/t/unable-to-find-nse-quote-meta-api/702/4
    if (symbol in INDICES) and (optionType == "Fut"):
        dates = expiry_list(symbol="RELIANCE", type="list")
        if expiryDate == "latest":
            expiryDate = dates[0]
        if expiryDate == "next":
            expiryDate = dates[1]

    if (expiryDate == "latest") or (expiryDate == "next"):
        dates = list(set((payload["expiryDates"])))
        dates.sort(key=lambda date: datetime.strptime(date, "%d-%b-%Y"))
        if expiryDate == "latest":
            expiryDate = dates[0]
        if expiryDate == "next":
            expiryDate = dates[1]

    meta = "Options"
    if optionType == "Fut":
        meta = "Futures"
    if optionType == "PE":
        optionType = "Put"
    if optionType == "CE":
        optionType = "Call"

    if optionType != "-":
        for stock in payload["stocks"]:
            stock_meta_data = stock["metadata"]
            if meta in stock_meta_data["instrumentType"]:
                if optionType == "Fut" and stock_meta_data["expiryDate"] == expiryDate:
                    metadata = stock_meta_data
                elif (
                    optionType in ["Put", "Call"]
                    and stock_meta_data["expiryDate"] == expiryDate
                    and stock_meta_data["optionType"] == optionType
                    and stock_meta_data["strikePrice"] == strikePrice
                ):
                    metadata = stock_meta_data

    if optionType == "-":
        # TODO: is payload["metadata"] correct? In the original script it is i["metadata"]
        # which, when looked at closely, is out side the loop & looks incorrect.
        metadata = payload["metadata"]

    return metadata


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


def nse_results(
    index: str = "equities",
    period: str = "Quarterly",
) -> Union[pd.DataFrame, None]:
    if index in ["equities", "debt", "sme"]:
        if period in ["Quarterly", "Annual", "Half-Yearly", "Others"]:
            payload = nsefetch(
                url=f"{CORPORATES_FINANCIAL_RESULTS_URL}{index}&period={period}",
            )
            return pd.json_normalize(payload)
        else:
            print("Give Correct Period Input")
    else:
        print("Give Correct Index Input")


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


def nsetools_get_quote(symbol: str) -> Union[dict, None]:
    payload = nsefetch(url=POSITIONS_URL)
    for data in payload["data"]:
        if data["symbol"] == symbol.upper():
            return data


def nse_index() -> pd.DataFrame:
    payload = nsefetch(url=LIVE_INDICIES_WATCH_URL)
    return pd.DataFrame(payload["data"])


def nse_get_index_list() -> list[str]:
    payload = nsefetch(LIVE_INDICIES_WATCH_URL)
    payload = pd.DataFrame(payload["data"])
    return payload["indexName"].tolist()


def nse_get_index_quote(index: str) -> Union[dict, None]:
    payload = nsefetch(LIVE_INDICIES_WATCH_URL)
    for data in payload["data"]:
        if data["indexName"] == index.upper():
            return data


def nse_get_advances_declines(mode: str = "pandas") -> Union[pd.DataFrame, dict]:
    try:
        if mode == "pandas":
            positions = nsefetch(url=POSITIONS_URL)
            return pd.DataFrame(positions["data"])
        else:
            return nsefetch(url=POSITIONS_URL)
    except Exception as e:
        logging.info(msg=str(e))
        logging.info(msg="Pandas is not working for some reason.")
        return nsefetch(url=POSITIONS_URL)


def nse_get_top_losers() -> pd.DataFrame:
    positions = nsefetch(url=POSITIONS_URL)
    positions_df = pd.DataFrame(positions["data"]).sort_values(by="pChange")
    return positions_df.head(5)


def nse_get_top_gainers() -> pd.DataFrame:
    positions = nsefetch(url=POSITIONS_URL)
    positions_df = pd.DataFrame(positions["data"]).sort_values(
        by="pChange",
        ascending=False,
    )
    return positions_df.head(5)


def nse_get_fno_lot_sizes(
    symbol: str = "all",
    mode: str = "list",
) -> Union[pd.DataFrame, dict]:
    if mode == "list":
        s = requests.get(url=FO_MARKET_LOTS_URL).text
        res_dict = {}
        for line in s.split("\n"):
            if line and re.search(",", line) and (line.casefold().find("symbol") == -1):
                code, name = [x.strip() for x in line.split(",")[1:3]]
                res_dict[code] = int(name)
        if symbol == "all":
            return res_dict
        if symbol:
            return res_dict[symbol.upper()]

    if mode == "pandas":
        payload = pd.read_csv(url=FO_MARKET_LOTS_URL)
        if symbol == "all":
            return payload
        else:
            return payload[payload.iloc[:, 1] == symbol.upper()]


def whoistheboss() -> str:
    return "subhash"


def indiavix() -> Union[dict, None]:
    payload = nsefetch(url=ALL_INDICIES_URL)
    for data in payload["data"]:
        if data["index"] == "INDIA VIX":
            return data["last"]


def index_info(index: str) -> Union[dict, None]:
    payload = nsefetch(url=ALL_INDICIES_URL)
    for data in payload["data"]:
        if data["index"] == index:
            return data


# This function hasn't been modified from the original code.
def black_scholes_dexter(
    S0: Union[int, float],
    X: Union[int, float],
    t: Union[int, float],
    σ: str = "",
    r: Union[int, float] = 10,
    q: float = 0.0,
    td: Union[int, float] = 365,
) -> tuple:
    if not σ:
        σ = indiavix()

    S0, X, σ, r, q, t = (
        float(S0),
        float(X),
        float(σ / 100),
        float(r / 100),
        float(q / 100),
        float(t / td),
    )
    # https://unofficed.com/black-scholes-model-options-calculator-google-sheet/

    d1 = (math.log(S0 / X) + (r - q + 0.5 * σ**2) * t) / (σ * math.sqrt(t))
    # stackoverflow.com/questions/34258537/python-typeerror-unsupported-operand-types-for-float-and-int

    # stackoverflow.com/questions/809362/how-to-calculate-cumulative-normal-distribution
    Nd1 = (math.exp((-(d1**2)) / 2)) / math.sqrt(2 * math.pi)
    d2 = d1 - σ * math.sqrt(t)
    Nd2 = norm.cdf(d2)
    call_theta = (
        -(
            (S0 * σ * math.exp(-q * t))
            / (2 * math.sqrt(t))
            * (1 / (math.sqrt(2 * math.pi)))
            * math.exp(-(d1 * d1) / 2)
        )
        - (r * X * math.exp(-r * t) * norm.cdf(d2))
        + (q * math.exp(-q * t) * S0 * norm.cdf(d1))
    ) / td
    put_theta = (
        -(
            (S0 * σ * math.exp(-q * t))
            / (2 * math.sqrt(t))
            * (1 / (math.sqrt(2 * math.pi)))
            * math.exp(-(d1 * d1) / 2)
        )
        + (r * X * math.exp(-r * t) * norm.cdf(-d2))
        - (q * math.exp(-q * t) * S0 * norm.cdf(-d1))
    ) / td
    call_premium = math.exp(-q * t) * S0 * norm.cdf(d1) - X * math.exp(
        -r * t,
    ) * norm.cdf(d1 - σ * math.sqrt(t))
    put_premium = X * math.exp(-r * t) * norm.cdf(-d2) - math.exp(
        -q * t,
    ) * S0 * norm.cdf(-d1)
    call_delta = math.exp(-q * t) * norm.cdf(d1)
    put_delta = math.exp(-q * t) * (norm.cdf(d1) - 1)
    gamma = (
        (math.exp(-r * t) / (S0 * σ * math.sqrt(t)))
        * (1 / (math.sqrt(2 * math.pi)))
        * math.exp(-(d1 * d1) / 2)
    )
    vega = ((1 / 100) * S0 * math.exp(-r * t) * math.sqrt(t)) * (
        1 / (math.sqrt(2 * math.pi)) * math.exp(-(d1 * d1) / 2)
    )
    call_rho = (1 / 100) * X * t * math.exp(-r * t) * norm.cdf(d2)
    put_rho = (-1 / 100) * X * t * math.exp(-r * t) * norm.cdf(-d2)

    return (
        call_theta,
        put_theta,
        call_premium,
        put_premium,
        call_delta,
        put_delta,
        gamma,
        vega,
        call_rho,
        put_rho,
    )


def equity_history_virgin(
    symbol: str,
    series: str,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    # url="https://www.nseindia.com/api/historical/cm/equity?symbol="+symbol+"&series=[%22"+series+"%22]&from="+str(start_date)+"&to="+str(end_date)+""
    url = f"{HISTORICAL_EQUITY_URL}{symbol}&series=['{series}']&from={start_date}&to={end_date}"
    payload = nsefetch(url=url)
    return pd.DataFrame.from_records(payload["data"])


# You shall see beautiful use the logger function.
def equity_history(
    symbol: str,
    series: str,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    # We are getting the input in text. So it is being converted to Datetime object from String.
    start_date: datetime = datetime.strptime(start_date, "%d-%m-%Y")
    end_date: datetime = datetime.strptime(end_date, "%d-%m-%Y")
    logging.info(f"Starting Date: {start_date}")
    logging.info(f"Ending Date: {end_date}")

    # We are calculating the difference between the days
    total_days = (end_date - start_date).days
    logging.info(msg=f"Total Number of Days: {total_days}")
    total_loops = total_days / 40
    logging.info(msg=f"Total FOR Loops in the program: {total_loops}")
    remainder_loop = total_days - (total_loops * 40)
    logging.info(msg=f"Remainder Loop: {remainder_loop}")

    total = pd.DataFrame()
    for i in range(int(total_days / 40)):
        temp_date = (start_date + timedelta(days=40)).strftime("%d-%m-%Y")
        start_date = datetime.strftime(start_date, "%d-%m-%Y")

        logging.info(msg=f"Loop = {i}")
        logging.info(msg="====")
        logging.info(msg=f"Starting Date: {start_date}")
        logging.info(msg=f"Ending Date: {temp_date}")
        logging.info(msg="====")

        total = pd.concat(
            [
                total,
                equity_history_virgin(
                    symbol=symbol,
                    series=series,
                    start_date=start_date,
                    end_date=temp_date,
                ),
            ],
        )

        logging.info(f"Length of the Table: {len(total)}")

        # Preparation for the next loop
        start_date = datetime.strptime(temp_date, "%d-%m-%Y")

    start_date = datetime.strftime(start_date, "%d-%m-%Y")
    end_date = datetime.strftime(end_date, "%d-%m-%Y")

    logging.info(msg="End Loop")
    logging.info(msg="====")
    logging.info(msg=f"Starting Date: {start_date}")
    logging.info(msg=f"Ending Date: {end_date}")
    logging.info(msg="====")

    total = pd.concat(
        [
            total,
            equity_history_virgin(
                symbol=symbol,
                series=series,
                start_date=start_date,
                end_date=end_date,
            ),
        ],
    )

    logging.info(msg="Finale")
    logging.info(msg=f"Length of the Total Dataset: {len(total)}")
    return total.iloc[::-1].reset_index(drop=True)


def derivative_history_virgin(
    symbol: str,
    start_date: str,
    end_date: str,
    instrumentType: str,
    expiry_date: str,
    strikePrice: str = "",
    optionType: str = "",
) -> pd.DataFrame:

    if instrumentType.lower() == "options":
        instrumentType = "FUTSTK" if "NIFTY" in symbol else "OPTSTK"

    elif instrumentType.lower() == "futures":
        instrumentType = "OPTIDX" if "NIFTY" in symbol else "FUTIDX"

    if (instrumentType in ["OPTIDX", "OPTSTK"]) and expiry_date:
        strikePrice = str(round(strikePrice, 2))

    nsefetch_url = (
        f"{HISTORICAL_DERIVATIVES_URL}{start_date}&to={end_date}"
        f"&optionType={optionType}&strikePrice={strikePrice}"
        f"&expiryDate={expiry_date}&instrumentType={instrumentType}"
        f"&symbol={symbol}"
    )

    payload = nsefetch(url=nsefetch_url)
    logging.info(msg=f"{nsefetch_url}")
    logging.info(msg=f"{payload}")
    return pd.DataFrame.from_records(payload["data"])


def derivative_history(
    symbol: str,
    start_date: str,
    end_date: str,
    instrumentType: str,
    expiry_date: str,
    strikePrice: str = "",
    optionType: str = "",
) -> pd.DataFrame:
    # We are getting the input in text. So it is being converted to Datetime object from String.
    start_date: datetime = datetime.strptime(start_date, "%d-%m-%Y")
    end_date: datetime = datetime.strptime(end_date, "%d-%m-%Y")
    logging.info(f"Starting Date: {start_date}")
    logging.info(f"Ending Date: {end_date}")

    # We are calculating the difference between the days
    total_days = (end_date - start_date).days
    logging.info(msg=f"Total Number of Days: {total_days}")
    total_loops = total_days / 40
    logging.info(msg=f"Total FOR Loops in the program: {total_loops}")
    remainder_loop = total_days - (total_loops * 40)
    logging.info(msg=f"Remainder Loop: {remainder_loop}")

    total = pd.DataFrame()
    for i in range(int(total_days / 40)):
        temp_date = (start_date + timedelta(days=40)).strftime("%d-%m-%Y")
        start_date = datetime.strftime(start_date, "%d-%m-%Y")

        logging.info(msg=f"Loop = {i}")
        logging.info(msg="====")
        logging.info(msg=f"Starting Date: {start_date}")
        logging.info(msg=f"Ending Date: {temp_date}")
        logging.info(msg="====")

        total = pd.concat(
            [
                total,
                derivative_history_virgin(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=temp_date,
                    instrumentType=instrumentType,
                    expiry_date=expiry_date,
                    strikePrice=strikePrice,
                    optionType=optionType,
                ),
            ],
        )

        logging.info(f"Length of the Table: {len(total)}")

        # Preparation for the next loop
        start_date = datetime.strptime(temp_date, "%d-%m-%Y")

    start_date = datetime.strftime(start_date, "%d-%m-%Y")
    end_date = datetime.strftime(end_date, "%d-%m-%Y")

    logging.info(msg="End Loop")
    logging.info(msg="====")
    logging.info(msg=f"Starting Date: {start_date}")
    logging.info(msg=f"Ending Date: {end_date}")
    logging.info(msg="====")

    total = pd.concat(
        [
            total,
            derivative_history_virgin(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                instrumentType=instrumentType,
                expiry_date=expiry_date,
                strikePrice=strikePrice,
                optionType=optionType,
            ),
        ],
    )

    logging.info(msg="Finale")
    logging.info(msg=f"Length of the Total Dataset: {len(total)}")
    return total.iloc[::-1].reset_index(drop=True)


def expiry_history(symbol: str, start_date: str = "", end_date: str = "") -> list[str]:
    # TODO: is this correct? Shouldn't it be end_date = start_date, if end_date is an empty string?
    if not end_date:
        end_date = end_date
    nsefetch_url = (
        f"{HISTORICAL_DERIVATIVES_META_URL}{start_date}&to={end_date}&symbol={symbol}"
    )
    payload = nsefetch(url=nsefetch_url)
    return payload["data"][2]


def index_history(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    data = {
        "name": symbol,
        "startDate": start_date,
        "endDate": end_date,
    }
    data = json.dumps(data)
    payload = requests.post(
        url=GET_HISTORICAL_DATA_TABLE_TO_STRING_URL,
        headers=NIFTY_INDICIES_HEADERS,
        data=data,
    ).json()
    payload = json.loads(payload["d"])
    return pd.DataFrame.from_records(payload)


def index_pe_pb_div(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    data = {
        "name": symbol,
        "startDate": start_date,
        "endDate": end_date,
    }
    data = json.dumps(data)
    payload = requests.post(
        url=GET_PE_PB_HISTORICAL_DATA_DB_TO_STRING_URL,
        headers=NIFTY_INDICIES_HEADERS,
        data=data,
    ).json()
    payload = json.loads(payload["d"])
    return pd.DataFrame.from_records(payload)


def index_total_returns(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    data = {
        "name": symbol,
        "startDate": start_date,
        "endDate": end_date,
    }
    data = json.dumps(data)
    payload = requests.post(
        url=GET_TOTAL_RETURN_INDEX_STRING_URL,
        headers=NIFTY_INDICIES_HEADERS,
        data=data,
    ).json()
    payload = json.loads(payload["d"])
    return pd.DataFrame.from_records(payload)


def get_bhavcopy(date: str) -> pd.DataFrame:
    return pd.read_csv(SEC_BHAV_DATA_FULL_URL + date.replace("-", "") + ".csv")


def get_bulkdeals() -> pd.DataFrame:
    return pd.read_csv(BULK_DEALS_URL)


def get_blockdeals() -> pd.DataFrame:
    return pd.read_csv(BLOCK_DEALS_URL)


# Request from subhash
## https://unofficed.com/how-to-find-the-beta-of-indian-stocks-using-python/
def get_beta_df_maker(symbol: str, days: int) -> pd.DataFrame:
    if "NIFTY" in symbol:
        end_date = run_time.strftime("%d-%b-%Y")
        start_date = (run_time - timedelta(days=days)).strftime(
            "%d-%b-%Y",
        )

        index_history_df = index_history(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )
        index_history_df["daily_change"] = (
            index_history_df["CLOSE"].astype(float).pct_change()
        )
        return index_history_df.iloc[1:, ["HistoricalDate", "daily_change"]]
    else:
        end_date = run_time.strftime("%d-%m-%Y")
        start_date = (run_time - timedelta(days=days)).strftime(
            "%d-%m-%Y",
        )

        equity_history_df = equity_history(
            symbol=symbol,
            series="EQ",
            start_date=start_date,
            end_date=end_date,
        )

        equity_history_df["daily_change"] = equity_history_df[
            "CH_CLOSING_PRICE"
        ].pct_change()
        return equity_history_df.iloc[1:, ["CH_TIMESTAMP", "daily_change"]]


def getbeta(symbol: str, days: int = 365, symbol2: str = "NIFTY 50") -> float:
    return get_beta(symbol=symbol, days=days, symbol2=symbol2)


def get_beta(symbol: str, days: int = 365, symbol2: str = "NIFTY 50") -> float:
    # Default is 248 days. (Input of Subhash)
    symbol_df = get_beta_df_maker(symbol=symbol, days=days)
    symbol2_df = get_beta_df_maker(symbol=symbol2, days=days)

    symbol_daily_change = symbol_df["daily_change"]
    symbol2_daily_change = symbol2_df["daily_change"]

    # since x & y are pandas series, we get builtin cov() & var() functions
    covariance = symbol_daily_change.cov(symbol2_daily_change)
    variance = symbol2_daily_change.var()

    beta = covariance / variance
    return round(beta, 3)


def nse_preopen(
    key: str = "NIFTY",
    type: str = "pandas",
) -> Union[dict, pd.DataFrame]:
    payload = nsefetch(url=f"{MARKET_DATA_PRE_OPEN_URL}{key}")
    if type == "pandas":
        payload = pd.DataFrame(payload["data"])
        return pd.json_normalize(payload["metadata"])
    else:
        return payload


# By Avinash https://forum.unofficed.com/t/nsepython-documentation/376/102?u=dexter
def nse_preopen_movers(key: str = "FO", filter: float = 1.5) -> tuple:
    preOpen_gainer = nse_preopen(key=key)
    return (
        preOpen_gainer[preOpen_gainer["pChange"] > filter],
        preOpen_gainer[preOpen_gainer["pChange"] < -filter],
    )


# type = "securities"
# type = "etf"
# type = "sme"

# sort = "volume"
# sort = "value"


def nse_most_active(type: str = "securities", sort: str = "value") -> pd.DataFrame:
    payload = nsefetch(url=f"{LIVE_ANALYSIS_MOST_ACTIVE_URL}{type}?index={sort}")
    return pd.DataFrame(payload["data"])


def nse_eq_symbols() -> list:
    # https://forum.unofficed.com/t/feature-request-stocklist-api/1073/11
    eq_list_pd = pd.read_csv(EQUITY_LIST_URL)
    return eq_list_pd["SYMBOL"].tolist()
