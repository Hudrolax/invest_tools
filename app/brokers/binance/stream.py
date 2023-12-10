import asyncio
import json
from typing import Callable
import logging
import websockets

from utils import async_traceback_errors
from brokers.binance import BinanceTimeframes, BinanceBrokers, BinanceMarketStreamTypes

from core.config import (
    BINANCE_API_KEY,
    BINANCE_API_SECRET,
    BINANCE_SPOT_WSS,
    BINANCE_UM_WSS,
    BINANCE_CM_WSS,
)


logger = logging.getLogger('binance_stream')

@async_traceback_errors(logger)
async def market_stream(
    handler: Callable,
    broker: BinanceBrokers,
    symbol: str,
    stop_event: asyncio.Event,
    type: BinanceMarketStreamTypes,
    timeframe: BinanceTimeframes | None = None,
):
    """ The function runs websocket market stream
    Args:
        handler (Callable): handler func for handle the data
        symbol (str): Symbol name.
        timeframe (BinanceTimeframes | None): Kline data timeframe. Default None.
        type: BinanceMarketStreamTypes: Stream type.
        stop_event (asyncio.Event): stop event
    """
    symbol_name = symbol.lower()

    # choose broker
    if broker == 'Binance-spot':
        wss_base = BINANCE_SPOT_WSS
    elif broker == 'Binance-UM-Futures':
        wss_base = BINANCE_UM_WSS
    elif broker == 'Binance-CM-Futures':
        wss_base = BINANCE_CM_WSS
    else:
        raise ValueError(f'Wrong broker {broker}')

    # choose stream type
    if type == 'kline':
        url = f'{wss_base}/ws/{symbol_name}@kline_{timeframe}'
    elif type in ['ticker', 'trade']:
        url = f'{wss_base}/ws/{symbol_name}@{type}'
    else:
        raise ValueError(f'Wrong stream type: {type}')

    while not stop_event.is_set():
        try:
            async with websockets.connect(url) as ws:
                while not stop_event.is_set():
                    data = await ws.recv()
                    data = json.loads(data)
                    await handler(broker=broker, symbol=symbol, timeframe=timeframe, type=type, data=data)

        except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK):
            logger.warning("Connection closed, retrying...")
            await asyncio.sleep(1)  # waiting before reconnect
        except asyncio.CancelledError as e:
            raise e
        except Exception as e:
            logger.critical(f"An unexpected error from strategy: {e}")
            await asyncio.sleep(1)  # waiting before reconnect