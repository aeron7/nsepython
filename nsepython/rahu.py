import os,sys
# os.chdir(os.path.dirname(os.path.abspath(__file__)))
# sys.path.insert(1, os.path.join(sys.path[0], '..'))

import requests
import pandas as pd
import json

import random
import datetime,time
import logging
logging.basicConfig(level=logging.DEBUG)

# pd.set_option('display.max_columns', None)  # or 1000
# pd.set_option('display.max_rows', None)  # or 1000
# pd.set_option('display.max_colwidth', -1)  # or 199
# pd.options.mode.chained_assignment = None  # default='warn' https://stackoverflow.com/questions/20625582/how-to-deal-with-settingwithcopywarning-in-pandas

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
            print(output)
        except ValueError:
            s =requests.Session()
            output = s.get("http://nseindia.com",headers=headers)
            output = s.get(payload,headers=headers).json()
        return output

run_time=datetime.datetime.now()

#Constants
indices = ['NIFTY','NIFTYIT','BANKNIFTY']

def running_status():
    start_now=datetime.datetime.now().replace(hour=9, minute=15, second=0, microsecond=0)
    end_now=datetime.datetime.now().replace(hour=15, minute=45, second=0, microsecond=0)
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


def oi_data_builder():
    oi_data = pd.DataFrame()
    symbols=fnolist()

    for i, symbol in enumerate(symbols):
        #if(i>4):break #Tester
        logging.info("Fetching: "+symbol)
        payload = nse_optionchain_scrapper(symbol)

        m=0
        for m in range(len(payload['records']['data'])):
            try:
                try:
                    payload['records']['data'][m]['PE']['Type']='PE'
                    oi_data = oi_data.append(payload['records']['data'][m]['PE'],ignore_index=True)
                except:
                    pass
                try:
                    payload['records']['data'][m]['CE']['Type']='CE'
                    oi_data = oi_data.append(payload['records']['data'][m]['CE'],ignore_index=True)
                except:
                    pass
            except:
                logging.info(m)

    return oi_data

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

def nse_expirydetails(payload,i='0'):
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
  if(expiryDate=="latest") or (expiryDate=="next"):
    if(optionType!="Fut"):
      dates=list(set((payload["expiryDates"])))
      dates.sort(key = lambda date: datetime.datetime.strptime(date, '%d-%b-%Y'))
      expiryDate=dates[0]
      if(expiryDate=="next"):expiryDate=dates[1]

  meta = "Options"
  if(optionType=="Fut"): meta = "Futures"
  if(optionType=="PE"):optionType="Put"
  if(optionType=="CE"):optionType="Call"

  if(optionType!="-"):
      for i in payload['stocks']:
        if meta in i['metadata']['instrumentType']:
          #print(i['metadata'])
          if(expiryDate=="latest"):
            lastPrice = i['metadata']['lastPrice']
            break

          if (i['metadata']["expiryDate"]==expiryDate):
            if (i['metadata']["optionType"]==optionType):
              if (i['metadata']["strikePrice"]==strikePrice):
                #print(i['metadata'])
                lastPrice = i['metadata']['lastPrice']

  if(optionType=="-"):
      lastPrice = payload['underlyingValue']

  return lastPrice

  # print(nse_quote_ltp("BANKNIFTY"))
  # print(nse_quote_ltp("RELIANCE","latest","Fut"))
  # print(nse_quote_ltp("RELIANCE"))
  # print(nse_quote_ltp("BANKNIFTY","13-Aug-2020","PE",21000))
  # print(nse_quote_ltp("RELIANCE","latest","PE",2300))

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

def expiry_list(symbol):
    logging.info("Getting Expiry List of: "+ symbol)
    payload = nse_optionchain_scrapper(symbol,)
    payload = pd.DataFrame({'Date':payload['records']['expiryDates']})
    return
