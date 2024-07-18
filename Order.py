from get_binance_data import get_klines
from datetime import datetime, timezone, timedelta

def convert_unix_to_utc_plus_3(unix_timestamp):
    '''Convert Unix timestamp to datetime object in UTC'''
    
    dt_utc = datetime.fromtimestamp(int(unix_timestamp)/1000, tz=timezone.utc)
    utc_plus_3 = timezone(timedelta(hours=3))
    dt_utc_plus_3 = dt_utc.astimezone(utc_plus_3)
    return dt_utc_plus_3

class TestStrategyOrder:
    def __init__(self, symbol, entry_price, tp_price, sl_price, period, put_timestamp, strategy) -> None:
        self.symbol=symbol
        self.entry_price=entry_price
        self.period=period
        self.tp_price=tp_price
        self.sl_price=sl_price
        self.put_timestamp=put_timestamp # utc+3
        self.strategy=strategy
        
        self.entry_timestamp=None
        self.exit_timestamp=None
        self.profit=None
    
    def result(self):
        # 12h in trade till triger. Otherwise market sell
        if self.period=='15m':
            limit=720//15 # amount bars to see
            delta=900_000 # unix time = 15m
        elif self.period=='5m':
            limit=720//5
            delta=300_000

        klines_data=get_klines(self.symbol,self.period,limit,start_time=self.put_timestamp+delta)
        # if price stop falling 0.5 natr above entry many times, reject order
        # it happens when mm wants to create liquidity 
        # for kline in klines_data:
        # TODO: 

        # find possible entry time
        for kline in klines_data:
            if float(kline[3])<self.entry_price<float(kline[2]):
                self.entry_timestamp=kline[0]
                break
        
        # if order not placed in time (6h)
        if not self.entry_timestamp or self.entry_timestamp-self.put_timestamp>21_600_000:
            self.profit="expired"
            # print("expired: ", self.symbol, self.entry_price, self.strategy)
            return self.profit
        else:
            self.notify("fill")
        
        klines_data=get_klines(self.symbol,self.period,start_time=self.entry_timestamp+delta)
        for kline in klines_data:
            # stop loss trigger
            if float(kline[3])<self.sl_price<float(kline[2]):
                self.profit=(float(self.sl_price)-float(self.entry_price))/float(self.entry_price)
                self.exit_timestamp=kline[0]
                self.notify("sl")
                break
            # take profit trigger
            if float(kline[3])<self.tp_price<float(kline[2]):
                self.profit=(float(self.tp_price)-float(self.entry_price))/float(self.entry_price)
                self.exit_timestamp=kline[0]
                self.notify("tp")
                break

        # if order placed, but too big tp/sl. Time exceed. market sell
        if self.profit==None:
            self.profit=(float(self.sl_price)-float(self.entry_price))/float(self.entry_price)
            self.notify("sl")
            # TODO: profit= close-entry
        
        return self.profit

    def notify(self,message):
        pass
        if message=="fill":
            print(convert_unix_to_utc_plus_3(self.entry_timestamp))
            print("order filled", self.symbol, self.entry_price, self.tp_price, self.sl_price , '\n')
        elif self.exit_timestamp==None:
            print("still in trade", self.symbol, '\n')
        elif message=="tp":
            print(convert_unix_to_utc_plus_3(self.exit_timestamp))
            print("order tp", self.symbol, self.profit,'\n')
        elif message=="sl":
            print(convert_unix_to_utc_plus_3(self.exit_timestamp))
            print("order sl", self.symbol, self.profit, '\n')
        
# TODO: binance client real orders
#       save orders to file, delete after time limit 6h, or execute
#       run pumpbot every 6h with limit=100 on 15m timeframe