import numpy as np
from get_binance_data import get_all_futures_coins_info, get_klines, get_oi
from Order import TestStrategyOrder
from Order import convert_unix_to_utc_plus_3

def filter_coins(coins_info, volume_threshold=300_000_000):
    filtered_coins = [coin for coin in coins_info if \
        float(coin['quoteVolume']) >= volume_threshold and 'USDT' in coin['symbol']]
    return filtered_coins

def summarize_statistics(results):
    total_profit=0
    num_wins=0
    num_loses=0
    num_expired=0
    for result in results:
        if result=="expired":
            num_expired+=1
            continue
        
        total_profit+=float(result)
        if float(result)>0:
            num_wins+=1
        if float(result)<0:
            num_loses+=1
    
    return (total_profit,num_expired, num_wins, num_loses)

def find_growth_intervals_with_timestamps(values, cumulative_threshold, change_threshold, tolerance):
    """detects wide growth periods from list of values.
        
        tolerance - how many declined values in row are considered as bad. Big tolerance partially fixed with cutting. 
        cumulative_threshold - growth of values sublist
        change_treshold - treshold of value change to be accepted as growth
        
        appropriate parameters: 15m: 0.2, 0.01, 3   5m: 0.1,0.005,5"""
    change_intervals = []  # list of tuples
    start_index = 1

    while start_index < len(values)-tolerance:
        cumulative_change = 0
        decline_bar = 0 # amount declined in row bars
        # indexes of extremums are used to get accurate interval of growth
        min_value_index = start_index 
        max_value_index = start_index
        
        # start intervals only with change >=threshold
        if (float(values[start_index]) - float(values[start_index-1])) / float(values[start_index-1])<change_threshold:
            start_index+=1
            continue
        
        for iterator_index in range(start_index+1, len(values)):
            value_change_percent=(float(values[iterator_index]) - float(values[iterator_index-1])) / float(values[iterator_index-1])
            if float(values[iterator_index])>float(values[max_value_index]):
                max_value_index=iterator_index
            if float(values[iterator_index])<float(values[min_value_index]):
                min_value_index=iterator_index-1
            cumulative_change=(float(values[iterator_index]) - float(values[start_index])) / float(values[start_index])
            
            # if value grow
            if value_change_percent > change_threshold:
                decline_bar=max(0,decline_bar-2)
            # penalty for declined value
            elif value_change_percent<0:
                decline_bar+=1
            # extra penalty for big decline
            elif value_change_percent<(0-change_threshold):
                decline_bar+=1
            # little penalty for little growth
            elif value_change_percent>0:
                decline_bar+=0.25
            
            # if too much declined bars or pump is going right now
            if decline_bar>=tolerance or iterator_index==(len(values)-1):
                if ((float(values[max_value_index])-float(values[min_value_index]))/float(values[min_value_index])) > cumulative_threshold:
                    # cut edge decline/stagnate bars. Take precise growth period
                    change_intervals.append((cumulative_change, min_value_index, max_value_index))
                    min_value_index = len(values)-1
                    max_value_index = 0 
                # end propogation with this start_index
                break
               
        # move start further
        start_index=min_value_index+1
    
    return change_intervals

def vertical_volume_distribution(symbol, start_time, end_time, num_bins): 
    klines_data=get_klines(symbol,'1m',start_time=start_time,end_time=end_time)
    avg_price=[]
    volume=[]
    
    for kline in klines_data:
        avg_price.append((float(kline[1])+float(kline[4]))/2)
        volume.append(float(kline[5]))
    
    vertical_volume, bins = np.histogram(avg_price, bins=num_bins, weights=volume)
    return vertical_volume, bins

def calc_natr(symbol, period, end_time, limit=30):
    klines_data=get_klines(symbol,period,limit+1,end_time=end_time)
    if len(klines_data)!=limit+1:
        limit=len(klines_data)-1
    highs=[kline[2] for kline in klines_data]
    lows=[kline[3] for kline in klines_data]
    closes=[kline[4] for kline in klines_data]
    
    # Calculate True Range (TR)
    trs = []
    for i in range(1, len(klines_data)):
        high = float(highs[i])
        low = float(lows[i])
        close_prev = float(closes[i-1])
        tr = max(high - low, abs(high - close_prev), abs(low - close_prev))
        trs.append(tr)
    
    # Calculate Average True Range (ATR) using the moving average
    atrs = []
    for i in range(limit, len(trs) + 1):
        atr = sum(trs[i-limit:i]) / limit
        atrs.append(atr)
    
    # Normalize ATR (NATR)
    natrs = [atr / float(closes[i + limit]) for i, atr in enumerate(atrs)]
    
    return natrs[-1]

def pumpbot(symbol, period, limit, tp_natr_coef, sl_natr_coef,cumulative_threshold,change_threshold,tolerance, bin_coef, price_type, strategy):
    klines_data=get_klines(symbol,period,limit)
    timestamps=[] # list of unix timestamps for given period
    timestamps = [entry[0] for entry in klines_data]
    orders=[]
    
    # get data from binance
    oi_data = get_oi(symbol, period, limit)

    oi_values = [entry['sumOpenInterest'] for entry in oi_data]
    oi_rise_intervals_with_timestamps = find_growth_intervals_with_timestamps(oi_values, cumulative_threshold, change_threshold, tolerance)
    
    if price_type=="avgHL":
        price_values=[(float(kline[2])+float(kline[3]))/2 for kline in klines_data]
    elif price_type=="avgOC":
        price_values=[(float(kline[1])+float(kline[4]))/2 for kline in klines_data]
    elif price_type=="high":
        price_values=[float(kline[2]) for kline in klines_data]
    elif price_type=='low':
        price_values = [float(kline[3]) for kline in klines_data] 
    else:
        raise ValueError("wrong type of price")
        
    price_rise_intervals_with_timestamps = find_growth_intervals_with_timestamps(price_values, cumulative_threshold, change_threshold, tolerance)
    
    # aggregate corresponding intervals into one more precise
    rise_intervals=[] 
    if len(oi_rise_intervals_with_timestamps)!=0 and len(price_rise_intervals_with_timestamps)!=0:
        for oi_change, start_index1, end_index1 in oi_rise_intervals_with_timestamps:
            # for each oi rise interval, find price rise interval
            for price_change, start_index2, end_index2 in price_rise_intervals_with_timestamps:
                if abs(start_index1-start_index2)<=tolerance*2 or abs(end_index1-end_index2)<=tolerance*2:
                    amount_bins=int(price_change*100*bin_coef)
                    start_index=max(start_index1,start_index2)
                    end_index=min(end_index1,end_index2)
                    
                    # if not appropriate interval, skip
                    if start_index>=end_index:
                        continue
                    rise_intervals.append((start_index,end_index,amount_bins))
                    break

    # Put orders. Entry is weighted average or poc
    for start_index, end_index, amount_bins in rise_intervals:
        start_unix=timestamps[start_index]
        end_unix=timestamps[end_index]
        vertical_volume, bins = vertical_volume_distribution(symbol,start_unix,end_unix,amount_bins)
        print(symbol, period, "interval:", convert_unix_to_utc_plus_3(start_unix),convert_unix_to_utc_plus_3(end_unix))

        bins=np.array(bins, dtype=float)
        vertical_volume=np.array(vertical_volume,dtype=float)
        natr = calc_natr(symbol,period,end_unix)
        
        if strategy=="wa":
            weigthed_average=np.average(bins[:-1], weights=vertical_volume)
            tp_price=weigthed_average*(1+tp_natr_coef*natr)
            sl_price=weigthed_average*(1-sl_natr_coef*natr)
            orders.append(TestStrategyOrder(symbol,weigthed_average,tp_price,sl_price,period,end_unix,"wa"))
        elif strategy=="poc":
            poc=bins[np.argmax(vertical_volume)]
            tp_price=poc*(1+tp_natr_coef*natr)
            sl_price=poc*(1-sl_natr_coef*natr)
            orders.append(TestStrategyOrder(symbol,poc,tp_price,sl_price,period,end_unix,"poc"))
    
    return orders

def pumpbot_parameters_search(symbols, periods, limits, tp_natr_coefs, sl_natr_coefs,cumulative_thresholds,change_thresholds,tolerances, num_bins, price_indexes, strategies):
    parameters_statistics = {}
    # TODO: rewrite using built-in
    for price_index in price_indexes:
        for cumulative_threshold in cumulative_thresholds:
            for change_threshold in change_thresholds:
                for tolerance in tolerances:
                    for limit in limits:
                        for tp_natr_coef in tp_natr_coefs:
                            for sl_natr_coef in sl_natr_coefs:
                                for num_bin in num_bins:
                                    for strategy in strategies:
                                        for period in periods:
                                            # execute for all coins with this set of parameters
                                            orders=[]
                                            for symbol in symbols:
                                                order = pumpbot(symbol, period, limit, tp_natr_coef, sl_natr_coef, cumulative_threshold, change_threshold, tolerance, num_bin, price_index, strategy)
                                                orders+=order
                                            results = [order.result() for order in orders]
                                            
                                            statistics = summarize_statistics(results)
                                            params=(period, limit, tp_natr_coef, sl_natr_coef, cumulative_threshold, change_threshold, tolerance, num_bin, price_index, strategy)
                                            parameters_statistics[params] = statistics
    return parameters_statistics

def pumpbot_multiproccessed(parameters):
    # get coins with high volume traded
    all_futures_coins_info = get_all_futures_coins_info()
    filtered_coins = filter_coins(all_futures_coins_info)
    symbols = [coin['symbol'] for coin in filtered_coins]

    parameters_statistics={}
    for params in parameters:
        orders=[]
        period, limit, tp_natr_coef, sl_natr_coef,cumulative_threshold,change_threshold,tolerance, num_bin, price_index, strategy = params
        for symbol in symbols:
            order = pumpbot(symbol, period, limit, tp_natr_coef, sl_natr_coef,cumulative_threshold,change_threshold,tolerance, num_bin, price_index, strategy)
            orders+=order
            
        results = [order.result() for order in orders]
        statistics = summarize_statistics(results)
        parameters_statistics[params] = statistics
    
    return parameters_statistics

# TODO: autorun script
