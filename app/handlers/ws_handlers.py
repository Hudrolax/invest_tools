from brokers.binance import (
    BinanceTimeframe,
    BinanceBroker,
    BinanceMarketStreamType,
    BINANCE_BROKERS,
)
from brokers.bybit import BybitTimeframe, BybitBroker, BybitStreamType, BYBIT_BROKERS
from .alerts import handle_alerts
from .rates import handle_rates


async def ws_kline_handler(
    broker: BinanceBroker | BybitBroker,
    symbol: str,
    data: dict,
    stream_type: BinanceMarketStreamType | BybitStreamType,
    timeframe: BinanceTimeframe | BybitTimeframe | None = None,
) -> None:
    """This handler do things when recived updated kline from stream"""
    print(f"Kline update got from {broker} {symbol} {timeframe}")


async def ws_trade_handler(
    broker: BinanceBroker | BybitBroker,
    symbol: str,
    data: dict,
    stream_type: BinanceMarketStreamType | BybitStreamType,
    timeframe: BinanceTimeframe | BybitTimeframe | None = None,
) -> None:
    """This handler do things when recived updated trade from stream"""
    print(f"Trade update got from {broker} {symbol}")


async def ws_ticker_handler(
    broker: BinanceBroker | BybitBroker,
    symbol: str,
    data: dict,
    stream_type: BinanceMarketStreamType | BybitStreamType,
    timeframe: BinanceTimeframe | BybitTimeframe | None = None,
) -> None:
    """This handler do things when recived updated trade from stream"""
    if stream_type not in ['ticker', 'Ticker', 'Trade']:
        return

    if broker in BINANCE_BROKERS:
        last_price = data["c"]
    elif broker in BYBIT_BROKERS:
        if (
            data.get("topic")
            and data["topic"].replace(symbol, "") == "publicTrade."
            and data["type"] == "snapshot"
        ):
            last_price = data["data"][-1]["p"]
        else:
            return
    else:
        raise ValueError(f"wrond broker {broker}")

    # handling alerts
    await handle_alerts(broker, symbol, last_price)
    await handle_rates(broker, symbol, last_price)
