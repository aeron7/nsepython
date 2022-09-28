import os,sys
# os.chdir(os.path.dirname(os.path.abspath(__file__)))
# sys.path.insert(1, os.path.join(sys.path[0], '..'))

import requests
import pandas as pd
import json
import random
import datetime,time
import logging
import re

mode ='local'

if(mode=='local'):

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

    def nsefetch(payload):
        try:
            output = requests.get(payload,headers=headers).json()
            #print(output)
        except ValueError:
            s =requests.Session()
            output = s.get("http://nseindia.com",headers=headers)
            output = s.get(payload,headers=headers).json()
        return output

run_time=datetime.datetime.now()

#Constants
indices = ['NIFTY','FINNIFTY','BANKNIFTY']










def running_status():
    start_now=datetime.datetime.now().replace(hour=9, minute=15, second=0, microsecond=0)
    end_now=datetime.datetime.now().replace(hour=15, minute=30, second=0, microsecond=0)
    return start_now<datetime.datetime.now()<end_now

#Getting FNO Symboles
def fnolist():
    # df = pd.read_csv("https://www1.nseindia.com/content/fo/fo_mktlots.csv")
    # return [x.strip(' ') for x in df.drop(df.index[3]).iloc[:,1].to_list()]

    positions = nsefetch('https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O')

    nselist=['NIFTY','NIFTYIT','BANKNIFTY']

    i=0
    for x in range(i, len(positions['data'])):
        nselist=nselist+[positions['data'][x]['symbol']]

    return nselist

def nsesymbolpurify(symbol):
    symbol = symbol.replace('&','%26') #URL Parse for Stocks Like M&M Finance
    return symbol

def nse_optionchain_scrapper(symbol):
    symbol = nsesymbolpurify(symbol)
    if any(x in symbol for x in indices):
        payload = nsefetch('https://www.nseindia.com/api/option-chain-indices?symbol='+symbol)
    else:
        payload = nsefetch('https://www.nseindia.com/api/option-chain-equities?symbol='+symbol)
    return payload


def oi_chain_builder (symbol,expiry="latest",oi_mode="full"):

    payload = nse_optionchain_scrapper(symbol)

    if(oi_mode=='compact'):
        col_names = ['CALLS_OI','CALLS_Chng in OI','CALLS_Volume','CALLS_IV','CALLS_LTP','CALLS_Net Chng','Strike Price','PUTS_OI','PUTS_Chng in OI','PUTS_Volume','PUTS_IV','PUTS_LTP','PUTS_Net Chng']
    if(oi_mode=='full'):
        col_names = ['CALLS_Chart','CALLS_OI','CALLS_Chng in OI','CALLS_Volume','CALLS_IV','CALLS_LTP','CALLS_Net Chng','CALLS_Bid Qty','CALLS_Bid Price','CALLS_Ask Price','CALLS_Ask Qty','Strike Price','PUTS_Bid Qty','PUTS_Bid Price','PUTS_Ask Price','PUTS_Ask Qty','PUTS_Net Chng','PUTS_LTP','PUTS_IV','PUTS_Volume','PUTS_Chng in OI','PUTS_OI','PUTS_Chart']
    oi_data = pd.DataFrame(columns = col_names)

    #oi_row = {'CALLS_OI':0, 'CALLS_Chng in OI':0, 'CALLS_Volume':0, 'CALLS_IV':0, 'CALLS_LTP':0, 'CALLS_Net Chng':0, 'Strike Price':0, 'PUTS_OI':0, 'PUTS_Chng in OI':0, 'PUTS_Volume':0, 'PUTS_IV':0, 'PUTS_LTP':0, 'PUTS_Net Chng':0}
    oi_row = {'CALLS_OI':0, 'CALLS_Chng in OI':0, 'CALLS_Volume':0, 'CALLS_IV':0, 'CALLS_LTP':0, 'CALLS_Net Chng':0, 'CALLS_Bid Qty':0,'CALLS_Bid Price':0,'CALLS_Ask Price':0,'CALLS_Ask Qty':0,'Strike Price':0, 'PUTS_OI':0, 'PUTS_Chng in OI':0, 'PUTS_Volume':0, 'PUTS_IV':0, 'PUTS_LTP':0, 'PUTS_Net Chng':0,'PUTS_Bid Qty':0,'PUTS_Bid Price':0,'PUTS_Ask Price':0,'PUTS_Ask Qty':0}
    if(expiry=="latest"):
        expiry = payload['records']['expiryDates'][0]
    m=0
    for m in range(len(payload['records']['data'])):
        if(payload['records']['data'][m]['expiryDate']==expiry):
            if(1>0):
                try:
                    oi_row['CALLS_OI']=payload['records']['data'][m]['CE']['openInterest']
                    oi_row['CALLS_Chng in OI']=payload['records']['data'][m]['CE']['changeinOpenInterest']
                    oi_row['CALLS_Volume']=payload['records']['data'][m]['CE']['totalTradedVolume']
                    oi_row['CALLS_IV']=payload['records']['data'][m]['CE']['impliedVolatility']
                    oi_row['CALLS_LTP']=payload['records']['data'][m]['CE']['lastPrice']
                    oi_row['CALLS_Net Chng']=payload['records']['data'][m]['CE']['change']
                    if(oi_mode=='full'):
                        oi_row['CALLS_Bid Qty']=payload['records']['data'][m]['CE']['bidQty']
                        oi_row['CALLS_Bid Price']=payload['records']['data'][m]['CE']['bidprice']
                        oi_row['CALLS_Ask Price']=payload['records']['data'][m]['CE']['askPrice']
                        oi_row['CALLS_Ask Qty']=payload['records']['data'][m]['CE']['askQty']
                except KeyError:
                    oi_row['CALLS_OI'], oi_row['CALLS_Chng in OI'], oi_row['CALLS_Volume'], oi_row['CALLS_IV'], oi_row['CALLS_LTP'],oi_row['CALLS_Net Chng']=0,0,0,0,0,0
                    if(oi_mode=='full'):
                        oi_row['CALLS_Bid Qty'],oi_row['CALLS_Bid Price'],oi_row['CALLS_Ask Price'],oi_row['CALLS_Ask Qty']=0,0,0,0
                    pass

                oi_row['Strike Price']=payload['records']['data'][m]['strikePrice']

                try:
                    oi_row['PUTS_OI']=payload['records']['data'][m]['PE']['openInterest']
                    oi_row['PUTS_Chng in OI']=payload['records']['data'][m]['PE']['changeinOpenInterest']
                    oi_row['PUTS_Volume']=payload['records']['data'][m]['PE']['totalTradedVolume']
                    oi_row['PUTS_IV']=payload['records']['data'][m]['PE']['impliedVolatility']
                    oi_row['PUTS_LTP']=payload['records']['data'][m]['PE']['lastPrice']
                    oi_row['PUTS_Net Chng']=payload['records']['data'][m]['PE']['change']
                    if(oi_mode=='full'):
                        oi_row['PUTS_Bid Qty']=payload['records']['data'][m]['PE']['bidQty']
                        oi_row['PUTS_Bid Price']=payload['records']['data'][m]['PE']['bidprice']
                        oi_row['PUTS_Ask Price']=payload['records']['data'][m]['PE']['askPrice']
                        oi_row['PUTS_Ask Qty']=payload['records']['data'][m]['PE']['askQty']
                except KeyError:
                    oi_row['PUTS_OI'], oi_row['PUTS_Chng in OI'], oi_row['PUTS_Volume'], oi_row['PUTS_IV'], oi_row['PUTS_LTP'],oi_row['PUTS_Net Chng']=0,0,0,0,0,0
                    if(oi_mode=='full'):
                        oi_row['PUTS_Bid Qty'],oi_row['PUTS_Bid Price'],oi_row['PUTS_Ask Price'],oi_row['PUTS_Ask Qty']=0,0,0,0
            else:
                logging.info(m)

            if(oi_mode=='full'):
                oi_row['CALLS_Chart'],oi_row['PUTS_Chart']=0,0
            oi_data = oi_data.append(oi_row, ignore_index=True)

    return oi_data,float(payload['records']['underlyingValue']),payload['records']['timestamp']


def nse_quote(symbol):
    symbol = nsesymbolpurify(symbol)

    if any(x in symbol for x in fnolist()):
        payload = nsefetch('https://www.nseindia.com/api/quote-derivative?symbol='+symbol)
    else:
        payload = nsefetch('https://www.nseindia.com/api/quote-equity?symbol='+symbol)
    return payload

def nse_expirydetails(payload,i=0):
    currentExpiry = payload['records']['expiryDates'][i]
    currentExpiry = datetime.datetime.strptime(currentExpiry,'%d-%b-%Y').date()  # converting json datetime to alice datetime
    date_today = run_time.strftime('%Y-%m-%d')  # required to remove hh:mm:ss
    date_today = datetime.datetime.strptime(date_today,'%Y-%m-%d').date()
    dte = (currentExpiry - date_today).days
    return currentExpiry,dte

def pcr(payload,inp='0'):
    ce_oi = 0
    pe_oi = 0
    for i in payload['records']['data']:
        if i['expiryDate'] == payload['records']['expiryDates'][inp]:
            try:
                ce_oi += i['CE']['openInterest']
                pe_oi += i['PE']['openInterest']
            except KeyError:
                pass
    return pe_oi / ce_oi

def nse_quote_ltp(symbol,expiryDate="latest",optionType="-",strikePrice=0):
  payload = nse_quote(symbol)
  #https://stackoverflow.com/questions/7961363/removing-duplicates-in-lists
  #https://stackoverflow.com/questions/19199984/sort-a-list-in-python

  #BankNIFTY and NIFTY has weekly options. Using this Jugaad which has primary base of assumption that Reliance will not step out of FNO.
  #forum.unofficed.com/t/unable-to-find-nse-quote-meta-api/702/4
  if((symbol in indices) and (optionType=="Fut")):
    dates = expiry_list("RELIANCE","list")
    if(expiryDate=="latest"): expiryDate=dates[0]
    if(expiryDate=="next"): expiryDate=dates[1]

  if(expiryDate=="latest") or (expiryDate=="next"):
    dates=list(set((payload["expiryDates"])))
    dates.sort(key = lambda date: datetime.datetime.strptime(date, '%d-%b-%Y'))
    if(expiryDate=="latest"): expiryDate=dates[0]
    if(expiryDate=="next"): expiryDate=dates[1]

  meta = "Options"
  if(optionType=="Fut"): meta = "Futures"
  if(optionType=="PE"):optionType="Put"
  if(optionType=="CE"):optionType="Call"

  if(optionType!="-"):
      for i in payload['stocks']:
        if meta in i['metadata']['instrumentType']:
          #print(i['metadata'])
          if(optionType=="Fut"):
              if(i['metadata']['expiryDate']==expiryDate):
                lastPrice = i['metadata']['lastPrice']

          if((optionType=="Put")or(optionType=="Call")):
              if (i['metadata']["expiryDate"]==expiryDate):
                if (i['metadata']["optionType"]==optionType):
                  if (i['metadata']["strikePrice"]==strikePrice):
                    #print(i['metadata'])
                    lastPrice = i['metadata']['lastPrice']

  if(optionType=="-"):
      lastPrice = payload['underlyingValue']

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
  payload = nse_quote(symbol)
  #https://stackoverflow.com/questions/7961363/removing-duplicates-in-lists
  #https://stackoverflow.com/questions/19199984/sort-a-list-in-python

  #BankNIFTY and NIFTY has weekly options. Using this Jugaad which has primary base of assumption that Reliance will not step out of FNO.
  #forum.unofficed.com/t/unable-to-find-nse-quote-meta-api/702/4
  if((symbol in indices) and (optionType=="Fut")):
    dates = expiry_list("RELIANCE","list")
    if(expiryDate=="latest"): expiryDate=dates[0]
    if(expiryDate=="next"): expiryDate=dates[1]

  if(expiryDate=="latest") or (expiryDate=="next"):
    dates=list(set((payload["expiryDates"])))
    dates.sort(key = lambda date: datetime.datetime.strptime(date, '%d-%b-%Y'))
    if(expiryDate=="latest"): expiryDate=dates[0]
    if(expiryDate=="next"): expiryDate=dates[1]

  meta = "Options"
  if(optionType=="Fut"): meta = "Futures"
  if(optionType=="PE"):optionType="Put"
  if(optionType=="CE"):optionType="Call"

  if(optionType!="-"):
      for i in payload['stocks']:
        if meta in i['metadata']['instrumentType']:
          #print(i['metadata'])
          if(optionType=="Fut"):
              if(i['metadata']['expiryDate']==expiryDate):
                metadata = i['metadata']

          if((optionType=="Put")or(optionType=="Call")):
              if (i['metadata']["expiryDate"]==expiryDate):
                if (i['metadata']["optionType"]==optionType):
                  if (i['metadata']["strikePrice"]==strikePrice):
                    #print(i['metadata'])
                    metadata = i['metadata']

  if(optionType=="-"):
      metadata = i['metadata']

  return metadata

def nse_optionchain_ltp(payload,strikePrice,optionType,inp=0,intent=""):
    expiryDate=payload['records']['expiryDates'][inp]
    for x in range(len(payload['records']['data'])):
      if((payload['records']['data'][x]['strikePrice']==strikePrice) & (payload['records']['data'][x]['expiryDate']==expiryDate)):
          if(intent==""): return payload['records']['data'][x][optionType]['lastPrice']
          if(intent=="sell"): return payload['records']['data'][x][optionType]['bidprice']
          if(intent=="buy"): return payload['records']['data'][x][optionType]['askPrice']

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
    except KeyError:
        print("Getting Error While Fetching.")
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
    except KeyError:
        print("Getting Error While Fetching.")
    return payload

def quote_equity(symbol):
    return nse_eq(symbol)

def quote_derivative(symbol):
    return nse_fno(symbol)

def option_chain(symbol):
    return nse_optionchain_scrapper(symbol)

def nse_holidays(type="trading"):
    if(type=="clearing"):
        payload = nsefetch('https://www.nseindia.com/api/holiday-master?type=clearing')
    if(type=="trading"):
        payload = nsefetch('https://www.nseindia.com/api/holiday-master?type=trading')
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

def expiry_list(symbol,type="list"):
    logging.info("Getting Expiry List of: "+ symbol)

    if(type!="list"):
        payload = nse_optionchain_scrapper(symbol)
        payload = pd.DataFrame({'Date':payload['records']['expiryDates']})
        return payload

    if(type=="list"):
        payload = nse_quote(symbol)
        dates=list(set((payload["expiryDates"])))
        dates.sort(key = lambda date: datetime.datetime.strptime(date, '%d-%b-%Y'))
        return dates


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
    if(mode=="latest"):
        payload = nsefetch('https://nseindia.com/api/latest-circular')
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


def nse_index():
    payload = nsefetch('https://iislliveblob.niftyindices.com/jsonfiles/LiveIndicesWatch.json')
    payload = pd.DataFrame(payload["data"])
    return payload

def nse_get_index_list():
    payload = nsefetch('https://iislliveblob.niftyindices.com/jsonfiles/LiveIndicesWatch.json')
    payload = pd.DataFrame(payload["data"])
    return payload["indexName"].tolist()

def nse_get_index_quote(index):
    payload = nsefetch('https://iislliveblob.niftyindices.com/jsonfiles/LiveIndicesWatch.json')
    for m in range(len(payload['data'])):
        if(payload['data'][m]["indexName"] == index.upper()):
            return payload['data'][m]

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
    url="https://archives.nseindia.com/content/fo/fo_mktlots.csv"

    if(mode=="list"):
        s=requests.get(url).text
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
        payload = pd.read_csv(url)
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
    url="https://www.nseindia.com/api/historical/cm/equity?symbol="+symbol+"&series=[%22"+series+"%22]&from="+str(start_date)+"&to="+str(end_date)+""
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

        total=total.append(equity_history_virgin(symbol,series,start_date,temp_date))

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

    total=total.append(equity_history_virgin(symbol,series,start_date,end_date))

    logging.info("Finale")
    logging.info("Length of the Total Dataset: "+ str(len(total)))
    payload = total.iloc[::-1].reset_index(drop=True)
    return payload

def derivative_history_virgin(symbol,start_date,end_date,instrumentType,expiry_date,strikePrice="",optionType=""):

    instrumentType = instrumentType.lower()

    if(instrumentType=="options"):
        if("NIFTY" in symbol): instrumentType="FUTSTK"
        instrumentType="OPTSTK"
    if(instrumentType=="futures"):
        if("NIFTY" in symbol): instrumentType="OPTIDX"
        instrumentType="FUTIDX"

    if(((instrumentType=="OPTIDX")or (instrumentType=="OPTSTK")) and (expiry_date!="")):
        strikePrice = "%.2f" % strikePrice
        strikePrice = str(strikePrice)

    nsefetch_url = "https://www.nseindia.com/api/historical/fo/derivatives?&from="+str(start_date)+"&to="+str(end_date)+"&optionType="+optionType+"&strikePrice="+strikePrice+"&expiryDate="+expiry_date+"&instrumentType="+instrumentType+"&symbol="+symbol+""
    payload = nsefetch(nsefetch_url)
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

        total=total.append(derivative_history_virgin(symbol,start_date,temp_date,instrumentType,expiry_date,strikePrice,optionType))

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

    total=total.append(derivative_history_virgin(symbol,start_date,end_date,instrumentType,expiry_date,strikePrice,optionType))

    logging.info("Finale")
    logging.info("Length of the Total Dataset: "+ str(len(total)))
    payload = total.iloc[::-1].reset_index(drop=True)
    return payload


def expiry_history(symbol,start_date="",end_date=""):
    if(end_date==""):end_date=end_date
    nsefetch_url = "https://www.nseindia.com/api/historical/fo/derivatives/meta?&from="+start_date+"&to="+end_date+"&symbol="+symbol+""
    payload = nsefetch(nsefetch_url)
    return payload['data'][2]

# # Nifty Indicies Site

niftyindices_headers = {
    'Connection': 'keep-alive',
    'sec-ch-ua': '" Not;A Brand";v="99", "Google Chrome";v="91", "Chromium";v="91"',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'DNT': '1',
    'X-Requested-With': 'XMLHttpRequest',
    'sec-ch-ua-mobile': '?0',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36',
    'Content-Type': 'application/json; charset=UTF-8',
    'Origin': 'https://niftyindices.com',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Dest': 'empty',
    'Referer': 'https://niftyindices.com/reports/historical-data',
    'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8',
}

def index_history(symbol,start_date,end_date):
    data = "{'name':'"+symbol+"','startDate':'"+start_date+"','endDate':'"+end_date+"'}"
    payload = requests.post('https://niftyindices.com/Backpage.aspx/getHistoricaldatatabletoString', headers=niftyindices_headers,  data=data).json()
    payload = json.loads(payload["d"])
    payload=pd.DataFrame.from_records(payload)
    return payload

def index_pe_pb_div(symbol,start_date,end_date):
    data = "{'name':'"+symbol+"','startDate':'"+start_date+"','endDate':'"+end_date+"'}"
    payload = requests.post('https://niftyindices.com/Backpage.aspx/getpepbHistoricaldataDBtoString', headers=niftyindices_headers,  data=data).json()
    payload = json.loads(payload["d"])
    payload=pd.DataFrame.from_records(payload)
    return payload

def index_total_returns(symbol,start_date,end_date):
    data = "{'name':'"+symbol+"','startDate':'"+start_date+"','endDate':'"+end_date+"'}"
    payload = requests.post('https://niftyindices.com/Backpage.aspx/getTotalReturnIndexString', headers=niftyindices_headers,  data=data).json()
    payload = json.loads(payload["d"])
    payload=pd.DataFrame.from_records(payload)
    return payload

def get_bhavcopy(date):
    date = date.replace("-","")
    payload=pd.read_csv("https://archives.nseindia.com/products/content/sec_bhavdata_full_"+date+".csv")
    return payload

def get_bulkdeals():
    payload=pd.read_csv("https://archives.nseindia.com/content/equities/bulk.csv")
    return payload

def get_blockdeals():
    payload=pd.read_csv("https://archives.nseindia.com/content/equities/block.csv")
    return payload

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
    df = get_beta_df_maker(symbol,days)
    df2 = get_beta_df_maker(symbol2,days)

    x=df["daily_change"].tolist()
    y=df2["daily_change"].tolist()
    #stackoverflow.com/questions/42670055/is-there-any-better-way-to-calculate-the-covariance-of-two-lists-than-this
    mean_x = sum(x) / len(x)
    mean_y = sum(y) / len(y)
    covariance = sum((a - mean_x) * (b - mean_y) for (a,b) in zip(x,y)) / len(x)

    mean = sum(y) / len(y)
    variance = sum((i - mean) ** 2 for i in y) / len(y)

    beta = covariance/variance
    return round(beta,3)

def nse_preopen(key="NIFTY",type="pandas"):
    payload = nsefetch("https://www.nseindia.com/api/market-data-pre-open?key="+key+"")
    if(type=="pandas"):
        payload = pd.DataFrame(payload['data'])
        payload  = pd.json_normalize(payload['metadata'])
        return payload
    else:
        return payload

#By Avinash https://forum.unofficed.com/t/nsepython-documentation/376/102?u=dexter
def nse_preopen_movers(key="FO",filter=1.5):
    preOpen_gainer=nse_preopen(key)
    return preOpen_gainer[preOpen_gainer['pChange'] >1.5],preOpen_gainer[preOpen_gainer['pChange'] <-1.5]

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
