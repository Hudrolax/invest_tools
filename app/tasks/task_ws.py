# This module watching for symbols on DB and runs/stops streams for getting klines
import asyncio
from sqlalchemy import select, not_
from sqlalchemy.ext.asyncio import AsyncSession
from core.db import DatabaseSessionManager
import logging
from typing import Callable, Self
from datetime import datetime, timedelta, timezone

from utils import async_traceback_errors
from brokers.binance import (
    BinanceBroker,
    BinanceTimeframe,
    BinanceMarketStreamType,
    BINANCE_BROKERS,
)
from brokers.binance.stream import market_stream as binance_market_stream
from brokers.bybit import (
    BybitBroker,
    BybitTimeframe,
    BybitStreamType,
    BYBIT_BROKERS,
)
from brokers.bybit.stream import ticker_stream as bybit_ticker_stream
from handlers import ws_ticker_handler

from models.symbol import SymbolORM
from models.alert import AlertORM
from models.lines import LineORM


logger = logging.getLogger(__name__)


class StreamBase:
    def __init__(
        self,
        broker: BinanceBroker | BybitBroker,
        symbol: str,
        stream_type: BinanceMarketStreamType | BybitStreamType,
        timeframe: BinanceTimeframe | BybitTimeframe | None = None,
    ) -> None:
        self.broker: BinanceBroker | BybitBroker = broker
        self.symbol = symbol
        self.stream_type: BinanceMarketStreamType | BybitStreamType = (
            stream_type
        )
        self.timeframe: BinanceTimeframe | BybitTimeframe | None = timeframe
        self.stop_event = asyncio.Event()

        if stream_type == "kline" and not timeframe:
            ValueError(
                'If stream type is "kline" timeframe should be provided.'
            )

    async def run_stream(self, handler: Callable):
        raise NotImplementedError

    def stop(self):
        self.stop_event.set()

    def __eq__(self, __value: Self) -> bool:  # type: ignore
        return (
            self.broker == __value.broker
            and self.symbol == __value.symbol
            and self.stream_type == __value.stream_type
            and self.timeframe == __value.timeframe
        )

    def __str__(self) -> str:
        return f'{self.stream_type} stream {self.symbol}{f" {self.timeframe}" if self.timeframe else ''} ({self.broker})'


class BinanceStream(StreamBase):
    async def run_stream(self, handler: Callable):
        asyncio.create_task(
            binance_market_stream(
                handler=handler,
                broker=self.broker,  # type: ignore
                symbol=self.symbol,
                stream_type=self.stream_type,  # type: ignore
                timeframe=self.timeframe,  # type: ignore
                stop_event=self.stop_event,
            )
        )
        logger.info(f"{self} was started.")


class BybitStream(StreamBase):
    async def run_stream(self, handler: Callable):
        asyncio.create_task(
            bybit_ticker_stream(
                handler=handler,
                broker=self.broker,  # type: ignore
                symbol=self.symbol,
                stream_type=self.stream_type,  # type: ignore
                timeframe=self.timeframe,  # type: ignore
                stop_event=self.stop_event,
            )
        )
        logger.info(f"{self} was started.")


streams: list[BinanceStream | BybitStream] = []


@async_traceback_errors(logger)
async def get_actual_streams(
    db: AsyncSession,
) -> list[BinanceStream | BybitStream]:
    symbols = await SymbolORM.get_all(db)
    return [
        *[
            BinanceStream(
                broker=symbol.broker.name,
                symbol=str(symbol.name),
                stream_type="ticker",
            )
            for symbol in symbols
            if symbol.broker.name in BINANCE_BROKERS
        ],
        *[
            BybitStream(
                broker=symbol.broker.name,
                symbol=str(symbol.name),
                stream_type="Trade",
            )
            for symbol in symbols
            if symbol.broker.name in BYBIT_BROKERS
        ],
    ]


@async_traceback_errors(logger)
async def get_alerts_for_deleting(db: AsyncSession) -> list[AlertORM]:
    alerts = await AlertORM.get_filtered_alerts(db, is_active=False)
    one_month_ago = datetime.now(timezone.utc) - timedelta(days=30)
    alerts_for_deleting = [
        alert
        for alert in alerts
        if alert.triggered_at and alert.triggered_at < one_month_ago  # type: ignore
    ]
    return alerts_for_deleting


@async_traceback_errors(logger)
async def get_symbols_for_deleting(db: AsyncSession) -> list[SymbolORM]:
    query = (
        select(SymbolORM)
        .select_from(SymbolORM)
        .join(AlertORM, AlertORM.symbol_id == SymbolORM.id, isouter=True)
        .join(LineORM, LineORM.symbol_id == SymbolORM.id, isouter=True)
        .where(
            (AlertORM.id == None)
            & (LineORM.id == None)
            & not_(
                (
                    SymbolORM.name.in_(
                        [
                            "BTCUSDT",
                            "BTCUSD",
                            "BTCARS",
                            "ETHUSDT",
                            "ETHUSD",
                            "ETHBTC",
                            "USDTARS",
                            "USDRUB",
                            "USDTRUB",
                            "BTCRUB",
                        ]
                    )
                )
            )
        )
    )
    return [item[0] for item in (await db.execute(query)).all()]


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
                        print(f"delete stream {stream}")

                # start actual streams
                for actual_stream in actual_streams:
                    if actual_stream not in streams:
                        await actual_stream.run_stream(ws_ticker_handler)
                        streams.append(actual_stream)
                        print(f"append stream {actual_stream}")

            except Exception as ex:
                logger.critical(str(ex))

        await asyncio.sleep(60)
