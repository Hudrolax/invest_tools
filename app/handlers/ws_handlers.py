from brokers.binance import BinanceTimeframes, BinanceBrokers, BinanceMarketStreamTypes
from .alerts import handle_alerts
from .rates import handle_rates


async def ws_kline_handler(
    broker: BinanceBrokers,
    symbol: str,
    data: dict,
    type: BinanceMarketStreamTypes,
    timeframe: BinanceTimeframes | None = None,
) -> None:
    """This handler do things when recived updated kline from stream"""
    print(f'Kline update got from {broker} {symbol} {timeframe}')


async def ws_trade_handler(
    broker: BinanceBrokers,
    symbol: str,
    data: dict,
    type: BinanceMarketStreamTypes,
    timeframe: BinanceTimeframes | None = None,
) -> None:
    """This handler do things when recived updated trade from stream"""
    print(f'Trade update got from {broker} {symbol}')


async def ws_ticker_handler(
    broker: BinanceBrokers,
    symbol: str,
    data: dict,
    type: BinanceMarketStreamTypes,
    timeframe: BinanceTimeframes | None = None,
) -> None:
    """This handler do things when recived updated trade from stream"""

    # handling alerts
    await handle_alerts(broker, symbol, data['c'])
    await handle_rates(broker, symbol, data['c'])