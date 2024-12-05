# bybit WSS

import asyncio
import json
from typing import Callable
import logging
import hmac
import websockets
from datetime import datetime
import time

from utils import async_traceback_errors, log_error_with_traceback
from brokers.bybit import BybitBroker, BybitTimeframe, BybitStreamType, BYBIT_BROKER_MARKET_TYPE

from core.config import (
    BYBIT_PUBLIC_WSS_SPOT,
    BYBIT_PUBLIC_WSS_PERPETUAL,
    BYBIT_PUBLIC_WSS_INVERSE,
    BYBIT_API_KEY,
    BYBIT_API_SECRET,
    BYBIT_PRIVATE_WSS,
    BYBIT_TRADE_WSS,
)


logger = logging.getLogger("bybit_stream")


@async_traceback_errors(logger)
async def ticker_stream(
    handler: Callable,
    broker: BybitBroker,
    stop_event: asyncio.Event,
    stream_type: BybitStreamType,
    symbol: str | None = None,
    timeframe: BybitTimeframe | None = None,
):
    """The function runs websocket market stream
    Args:
        handler (Callable): handler func for handle the data
        symbol (str | None): Symbol name.
        timeframe (BybitTimeframe | None): Kline data timeframe. Default None.
        stop_event (asyncio.Event): stop event
    """

    # choose broker
    if stream_type in ["position", "order"]:
        wss_base = BYBIT_PRIVATE_WSS
    elif broker == "Bybit-spot":
        wss_base = BYBIT_PUBLIC_WSS_SPOT
    elif broker == "Bybit_perpetual":
        wss_base = BYBIT_PUBLIC_WSS_PERPETUAL
    elif broker == "Bybit-inverse":
        wss_base = BYBIT_PUBLIC_WSS_INVERSE
    else:
        raise ValueError(f"Wrong broker {broker}")

    while not stop_event.is_set():
        try:
            async with websockets.connect(wss_base) as ws:
                # Подписываемся на поток
                if stream_type in ["position", "order"]:
                    expires = int((time.time() + 1) * 1000)
                    signature = str(
                        hmac.new(
                            bytes(BYBIT_API_SECRET, "utf-8"),
                            bytes(f"GET/realtime{expires}", "utf-8"),
                            digestmod="sha256",
                        ).hexdigest()
                    )
                    auth_message = {"op": "auth", "args": [BYBIT_API_KEY, expires, signature]}
                    await ws.send(json.dumps(auth_message))
                    data = await asyncio.wait_for(ws.recv(), timeout=30)
                    data = json.loads(data)
                    if not (data.get("success") and data.get('op') == 'auth'):
                        raise RuntimeError(f'Не смог авторизоваться для подключения к потоку:\n{data}')

                    args = [f"{stream_type}.{BYBIT_BROKER_MARKET_TYPE[broker]}"]
                else:
                    if stream_type == "Kline" and symbol:
                        args = [f"kline.{timeframe}.{symbol.upper()}"]
                    elif stream_type == "Ticker" and symbol:
                        args = [f"tickers.{symbol.upper()}"]
                    elif stream_type == "Trade" and symbol:
                        args = [f"publicTrade.{symbol.upper()}"]
                    else:
                        raise ValueError(f"Wrong stream type {stream_type} or symbol is None (symbol: {symbol})")

                await ws.send(json.dumps({"op": "subscribe", "args": args}))
                data = await asyncio.wait_for(ws.recv(), timeout=30)
                data = json.loads(data)
                if data.get("success") is not None:
                    symbol_text = f" {symbol}" if symbol else ""
                    if data["success"]:
                        print(f"Подписались на поток {broker} {stream_type}{symbol_text} {timeframe}")
                    else:
                        print(f"Ошибка подписи на поток {broker} {stream_type}{symbol_text}:\n{data}")

                ping_time = datetime.now()
                while not stop_event.is_set():
                    try:
                        data = await asyncio.wait_for(ws.recv(), timeout=30)

                        # Обработка полученных данных
                        data = json.loads(data)
                        await handler(broker=broker, symbol=symbol, data=data, stream_type=stream_type, timeframe=timeframe)

                        time_delta = (datetime.now() - ping_time).total_seconds()
                        if time_delta >= 30:
                            # Отправляем пинг, чтобы поддержать соединение
                            await ws.send(json.dumps({"op": "ping"}))
                            ping_time = datetime.now()

                    except asyncio.TimeoutError as ex:
                        continue
                    except websockets.exceptions.ConnectionClosed as ex:
                        logger.error(f"Соединение потеряно (Разрыв соединения) {ex}, попытка переподключения...")
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
            log_error_with_traceback(logger, e)
            await asyncio.sleep(10)  # waiting before reconnect
