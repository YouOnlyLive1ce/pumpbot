import requests

def get_all_futures_coins_info():
    base_url = "https://fapi.binance.com"
    endpoint = "/fapi/v1/ticker/24hr"
    
    response = requests.get(base_url + endpoint)
    
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()
        
def get_klines(symbol, period, limit=500, start_time=None, end_time=None):
    if not hasattr(get_klines, "cached_last_500_candels"):
        get_klines.cached_last_500_candels={}
    # if asked before, than return from cache
    elif (symbol,period,limit) in get_klines.cached_last_500_candels.keys() and start_time==None and end_time==None:
        return get_klines.cached_last_500_candels[(symbol,period,limit)]
    
    # if first time asked, get from api
    base_url = "https://fapi.binance.com"
    endpoint = "/fapi/v1/klines"
    params = {
        'symbol': symbol,
        'interval': period,
        'limit': limit
    }
    if start_time:
        params['startTime']=start_time
    if end_time:
        params['endTime']=end_time
    
    # average response time ~1s
    response = requests.get(base_url + endpoint, params=params)
    
    # cache, if last 500 candels was asked
    if start_time==None and end_time==None:
        get_klines.cached_last_500_candels[(symbol,period,limit)]=response.json()
    
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()

def get_oi(symbol, period, limit=500):
    if not hasattr(get_oi, "cached_last_500_candels"):
        get_oi.cached_last_500_candels={}
    # if asked before, than return from cache
    elif (symbol,period,limit) in get_oi.cached_last_500_candels.keys():
        return get_oi.cached_last_500_candels[(symbol,period,limit)]
    
    # if first time asked, get from api
    base_url = "https://fapi.binance.com"
    endpoint = "/futures/data/openInterestHist"
    params = {
        'symbol': symbol,
        'period': period,
        'limit': limit
    }
    response = requests.get(base_url + endpoint, params=params)
    
    # cache last 500 candels
    get_oi.cached_last_500_candels[(symbol,period,limit)]=response.json()
    
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()