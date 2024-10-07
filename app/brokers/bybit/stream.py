# bybit WSS

import asyncio
import json
from typing import Callable
import logging
import websockets

from utils import async_traceback_errors
from brokers.bybit import BybitBroker, BybitTimeframe, BybitStreamType

from core.config import (
    BYBIT_WSS_SPOT,
    BYBIT_WSS_PERPETUAL,
    BYBIT_WSS_INVERSE,
)


logger = logging.getLogger("bybit_stream")


@async_traceback_errors(logger)
async def ticker_stream(
    handler: Callable,
    broker: BybitBroker,
    symbol: str,
    stop_event: asyncio.Event,
    stream_type: BybitStreamType,
    timeframe: BybitTimeframe | None = None,
):
    """The function runs websocket market stream
    Args:
        handler (Callable): handler func for handle the data
        symbol (str): Symbol name.
        timeframe (BybitTimeframe | None): Kline data timeframe. Default None.
        stop_event (asyncio.Event): stop event
    """

    # choose broker
    if broker == "Bybit-spot":
        wss_base = BYBIT_WSS_SPOT
    elif broker == "Bybit_perpetual":
        wss_base = BYBIT_WSS_PERPETUAL
    elif broker == "Bybit-inverse":
        wss_base = BYBIT_WSS_INVERSE
    else:
        raise ValueError(f"Wrong broker {broker}")

    while not stop_event.is_set():
        try:
            async with websockets.connect(wss_base) as ws:
                # Подписываемся на поток
                if stream_type == 'Kline':
                    args = [f'kline.{timeframe}.{symbol.upper()}']
                elif stream_type == 'Ticker':
                    args = [f'tickers.{symbol.upper()}']
                else:
                    raise ValueError(f"Wrong stream type {stream_type}")

                await ws.send(json.dumps({
                    'op': 'subscribe',
                    'args': args
                }))

                while not stop_event.is_set():
                    try:
                        data = await asyncio.wait_for(ws.recv(), timeout=30)

                        # Обработка полученных данных
                        data = json.loads(data)
                        await handler(broker=broker, symbol=symbol, data=data, stream_type=stream_type)

                        # Отправляем пинг, чтобы поддержать соединение
                        await ws.send(json.dumps({'op': 'ping'}))

                    except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed):
                        print("Соединение потеряно, попытка переподключения...")
                        break  # Выходим из цикла для переподключения

        except (
            websockets.exceptions.ConnectionClosedError,
            websockets.exceptions.ConnectionClosedOK,
        ):
            logger.warning("Connection closed, retrying...")
            await asyncio.sleep(1)  # waiting before reconnect
        except asyncio.CancelledError as e:
            raise e
        except Exception as e:
            logger.critical(f"An unexpected error from strategy: {e}")
            await asyncio.sleep(1)  # waiting before reconnect
