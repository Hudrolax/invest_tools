from brokers.binance import (
    BinanceTimeframe,
    BinanceBroker,
    BinanceMarketStreamType,
    BINANCE_BROKERS,
)
from brokers.bybit import (
    BybitTimeframe,
    BybitBroker,
    BybitStreamType,
    BYBIT_BROKERS,
)
from .alerts import handle_alerts
from .rates import handle_rates
from .positions import handle_positions
from .orders import handle_orders


async def ws_ticker_handler(
    broker: BinanceBroker | BybitBroker,
    symbol: str,
    data: dict,
    stream_type: BinanceMarketStreamType | BybitStreamType,
    timeframe: BinanceTimeframe | BybitTimeframe | None = None,
) -> None:
    """This handler do things when recived updated trade from stream"""
    if stream_type in ["ticker", "Ticker", "Trade"]:
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
    elif stream_type in ["position"]:
        await handle_positions(positions_data=data)
    elif stream_type in ["order"]:
        await handle_orders(orders_data=data)
