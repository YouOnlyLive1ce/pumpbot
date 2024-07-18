from pumpbot import pumpbot
from pumpbot import get_all_futures_coins_info
from pumpbot import filter_coins
from pumpbot import summarize_statistics

if __name__ == '__main__':    
    # get coins with high volume traded
    all_futures_coins_info = get_all_futures_coins_info()
    filtered_coins = filter_coins(all_futures_coins_info)
    symbols = [coin['symbol'] for coin in filtered_coins]
    tolerance = 6
    period = "15m"
    change_threshold = 0.01
    tp_natr_coef = 1.0 
    sl_natr_coef = 1.0
    bin_coef = 4
    price_type='avgHL'
    strategy='poc'
    cumulative_threshold = 0.1
    limit=500
    # TODO: instead of percent change,  consider coef * natr
    # TODO: placed, but no entry -> noentry_counter
    # improvements:
    # после обрезанных периодов еще раз проверять, больше ли они чем трешолд
    # наторговали уровень выше (2ч+) - отмена ордера

    # current changes:
    # avg=(2+3)/2
    # price_index
    orders=[]
    for symbol in symbols:
        orders+=pumpbot(symbol, period, limit, tp_natr_coef, sl_natr_coef,cumulative_threshold,change_threshold,tolerance, bin_coef, price_type, strategy)
    
    results=[order.result() for order in orders]

    print(summarize_statistics(results))
