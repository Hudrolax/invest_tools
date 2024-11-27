# write klines to DB
import logging

from core.db import sessionmanager
from brokers.bybit import BybitBroker, BybitTimeframe
from models.klines import KlineORM
from project_types import Kline

logger = logging.getLogger(__name__)

async def handle_kline(
    broker: BybitBroker,
    symbol: str,
    interval: BybitTimeframe,
    kline: Kline,
) -> None:
    async with sessionmanager.session() as db:
        await KlineORM.append_update(db, symbol_name=symbol, broker_name=broker, interval=interval, kline=kline)
