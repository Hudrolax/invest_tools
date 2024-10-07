from typing import Literal


BybitBroker = Literal['Bybit-spot', 'Bybit_perpetual', 'Bybit-inverse']
BYBIT_BROKERS = ['Bybit-spot', 'Bybit_perpetual', 'Bybit-inverse']
BybitTimeframe = Literal['1', '3', '5', '15', '30', '60', '120', '240', '360', '720', 'D', 'W', 'M'] 
BybitStreamType = Literal['Ticker', 'Kline']

bybit_symbols: dict[str, list[str]] = {
    'Bybit-spot': [],
    'Bybit_perpetual': [],
    'Bybit-inverse': [],
}

market_data: dict[str, dict] = {
    'Bybit-spot': {},
    'Bybit_perpetual': {},
    'Bybit-inverse': {},
}
