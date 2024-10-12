# write rates to DB
from decimal import Decimal
import logging
from datetime import datetime

from core.db import sessionmanager
from brokers.binance import BinanceBroker
from brokers.bybit import BybitBroker

from models.symbol import SymbolORM

logger = logging.getLogger(__name__)

async def handle_rates(
    broker: BinanceBroker | BybitBroker,
    symbol: str,
    last_price: Decimal | str | int | float,
) -> None:
    last_price = last_price if isinstance(last_price, Decimal) else Decimal(last_price)

    async with sessionmanager.session() as db:
        symbol_instance = await SymbolORM.get_by_name_and_broker(db, symbol, broker)
        await SymbolORM.update(db, symbol_instance.id, rate=last_price, last_update_time=datetime.now())
