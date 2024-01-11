# This module watching for symbols on DB and runs/stops streams for getting klines
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from core.db import DatabaseSessionManager
import logging
from typing import Callable, Self
from datetime import datetime, timedelta, UTC

from utils import async_traceback_errors
from brokers.binance import BinanceBrokers, BinanceTimeframes, BinanceMarketStreamTypes
from brokers.binance.stream import market_stream
from handlers import ws_ticker_handler

from models.symbol import SymbolORM
from models.alert import AlertORM

logger = logging.getLogger(__name__)


class BinanceStream:
    def __init__(self,
                 broker: BinanceBrokers,
                 symbol: str,
                 type: BinanceMarketStreamTypes,
                 timeframe: BinanceTimeframes | None = None
                 ) -> None:
        self.broker: BinanceBrokers = broker
        self.symbol = symbol
        self.type: BinanceMarketStreamTypes = type
        self.timeframe: BinanceTimeframes | None = timeframe
        self.stop_event = asyncio.Event()

        if type == 'kline' and not timeframe:
            ValueError(
                'If stream type is "kline" timeframe should be provided.')

    async def run_stream(self, handler: Callable):
        asyncio.create_task(market_stream(
            handler=handler,
            broker=self.broker,
            symbol=self.symbol,
            type=self.type,
            timeframe=self.timeframe,
            stop_event=self.stop_event,
        ))

        logger.info(f'{self} was started.')

    def stop(self):
        self.stop_event.set()

    def __eq__(self, __value: Self) -> bool:
        return self.broker == __value.broker and self.symbol == __value.symbol \
            and self.type == __value.type and self.timeframe == __value.timeframe

    def __str__(self) -> str:
        return f'{self.type} stream {self.symbol}{f" {self.timeframe}" if self.timeframe else ''} ({self.broker})'


streams: list[BinanceStream] = []


@async_traceback_errors(logger)
async def get_actual_streams(db: AsyncSession) -> list[BinanceStream]:
    return [
        BinanceStream(
            broker=symbol.broker.name,
            symbol=symbol.name,  # type: ignore
            type='ticker'
        ) for symbol in await SymbolORM.get_all(db)
    ]


@async_traceback_errors(logger)
async def get_alerts_for_deleting(db: AsyncSession) -> list[AlertORM]:
    alerts = await AlertORM.get_filtered_alerts(db, is_active=False)
    one_month_ago = datetime.utcnow().replace(tzinfo=UTC) - timedelta(days=1)
    alerts_for_deleting = [
        alert for alert in alerts if alert.triggered_at and alert.triggered_at < one_month_ago]  # type: ignore
    return alerts_for_deleting


@async_traceback_errors(logger)
async def get_symbols_for_deleting(db: AsyncSession) -> list[SymbolORM]:
    alerts = await AlertORM.get_filtered_alerts(db)
    alert_symbol_ids = {alert.symbol_id for alert in alerts}
    all_symbols = await SymbolORM.get_list(db)
    important_symbols = [
        'BTCUSDT',
        'BTCUSD',
        'BTCRUB',
        'BTCARS',
        'ETHUSDT',
        'ETHUSD',
        'ETHBTC',
        'USDTARS',
        'USDTRUB'
    ]
    symbols_for_deleting = [
        symbol for symbol in all_symbols if symbol.id not in alert_symbol_ids and symbol.name not in important_symbols]
    return symbols_for_deleting


async def task_run_market_streams(
    stop_event: asyncio.Event,
    sessionmaker: DatabaseSessionManager,
) -> None:
    while not stop_event.is_set():
        async with sessionmaker.session() as db:
            try:
                # delete old inactive alerts
                alerts_for_deleting = await get_alerts_for_deleting(db)
                for alert in alerts_for_deleting:
                    await alert.delete_self(db)

                # delete unactual symbols
                symbols_for_deleting = await get_symbols_for_deleting(db)
                for symbol in symbols_for_deleting:
                    await symbol.delete_self(db)

                # stop non actual streams
                actual_streams = await get_actual_streams(db)
                for i, stream in enumerate(streams):
                    if stream not in actual_streams:
                        stream.stop()
                        streams.pop(i)
                        print(f'delete stream {stream}')

                # start actuals streams
                for actual_stream in actual_streams:
                    if actual_stream not in streams:
                        await actual_stream.run_stream(ws_ticker_handler)
                        streams.append(actual_stream)
                        print(f'append stream {actual_stream}')

            except Exception as ex:
                logger.critical(str(ex))

        await asyncio.sleep(60)
