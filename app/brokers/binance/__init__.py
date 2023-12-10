from typing import Literal


BinanceBrokers = Literal['Binance-spot', 'Binance-UM-Futures', 'Binance-CM-Futures']
BinanceTimeframes = Literal['1s', '1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M'] 
BinanceMarketStreamTypes = Literal['kline', 'trade', 'ticker']

binance_symbols: dict[str, list[str]] = {
    'Binance-spot': [],
    'Binance-UM-Futures': [],
    'Binance-CM-Futures': [],
}

market_data: dict[str, dict] = {
    'Binance-spot': {},
    'Binance-UM-Futures': {},
    'Binance-CM-Futures': {},
}