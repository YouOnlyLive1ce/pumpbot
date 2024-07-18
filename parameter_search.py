import multiprocessing as mp
import pandas as pd
from pumpbot import get_all_futures_coins_info
from pumpbot import filter_coins
from pumpbot import pumpbot_parameters_search

if __name__ == '__main__':
    # get coins with high volume traded
    all_futures_coins_info = get_all_futures_coins_info()
    filtered_coins = filter_coins(all_futures_coins_info)
    symbols = [coin['symbol'] for coin in filtered_coins]
    
    tolerances = [2, 3, 4, 5, 6]
    periods = ["15m", "5m"]
    change_thresholds = [0.005, 0.01]  # low value give more intervals, but they will be wide
    tp_natr_coefs = [2, 1, 0.5]
    sl_natr_coefs = [1, 0.5, 0.25]
    num_bins = [40, 30]
    price_indexes=["high", "low", "avgHL"] #2="high", 3="low"
    strategies=['poc','wa']
    cumulative_thresholds = [0.1]
    limits=[500]
    
    # creating several proccesses to achieve better perfomance. results are aggregated in dictionary
    args = [(symbols, [p], limits, tp_natr_coefs, sl_natr_coefs,cumulative_thresholds,change_thresholds, [t], num_bins, price_indexes, strategies) for t in tolerances for p in periods]
    print(len(args))
    
    with mp.Pool(processes=10) as pool:
        results = pool.starmap(pumpbot_parameters_search, args)
        
    parameters_statistics = {}
    for result in results:
        parameters_statistics.update(result)
    data = []
    
    for key, value in parameters_statistics.items():
        data.append(list(key) + list(value))
        
    columns = ['period', 'limit', 'tp_natr_coef', 'sl_natr_coef', 'cumulative_threshold', 'change_threshold', 'tolerance',  'num_bin', 'price_index', 'strategy', 'profit', 'expired', '# win', '# lose']
    df = pd.DataFrame(data, columns=columns)
    df.to_csv('parameters_statistics-17-07.csv', index=False)
    print(df.head())
