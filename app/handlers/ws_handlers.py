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
from project_types import Kline
from handlers.klines import handle_kline


async def ws_ticker_handler(
    broker: BinanceBroker | BybitBroker,
    symbol: str,
    data: dict,
    stream_type: BinanceMarketStreamType | BybitStreamType,
    timeframe: BinanceTimeframe | BybitTimeframe | None = None,
) -> None:
    """This handler do things when recived updated trade from stream"""
    if stream_type in ["Trade"]:
        # tick on every deal
        if broker in BINANCE_BROKERS:
            pass
        elif broker in BYBIT_BROKERS:
            if data.get("topic") and data["topic"].replace(symbol, "") == "publicTrade." and data["type"] == "snapshot":
                last_price = data["data"][-1]["p"]
            else:
                return
        else:
            raise ValueError(f"wrond broker {broker}")
    elif stream_type in ["Kline"]:
        # last kline info. Push frequency: 1-60s
        if broker in BINANCE_BROKERS:
            pass
        elif broker in BYBIT_BROKERS:
            if data.get("topic"):
                topic, interval, symbol_name = data["topic"].split(".")
                if (
                    topic != "kline"
                    or interval != timeframe
                    or symbol_name != symbol
                    or not data.get("data")
                    or len(data["data"]) < 1
                ):
                    return
                kline_data = data["data"][-1]
                await handle_rates(broker, symbol, kline_data["close"])
                # await handle_kline(
                #     broker,  # type: ignore
                #     symbol,
                #     interval=timeframe,  # type: ignore
                #     kline=Kline(
                #         start=kline_data["start"],
                #         open=kline_data["open"],
                #         high=kline_data["high"],
                #         low=kline_data["low"],
                #         close=kline_data["close"],
                #     ),
                # )
                # await handle_alerts(broker, symbol, kline_data["close"])
            else:
                return
        else:
            raise ValueError(f"wrong broker {broker}")

    elif stream_type in ["position"]:
        await handle_positions(positions_data=data)
    elif stream_type in ["order"]:
        await handle_orders(orders_data=data)
