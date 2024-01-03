# write rates to DB
from decimal import Decimal
import logging

from core.db import sessionmanager
from brokers.binance import BinanceBrokers

from models.symbol import SymbolORM

logger = logging.getLogger(__name__)

async def handle_rates(
    broker: BinanceBrokers,
    symbol: str,
    last_price: Decimal | str | int | float,
) -> None:
    last_price = last_price if isinstance(last_price, Decimal) else Decimal(last_price)

    async with sessionmanager.session() as db:
        symbol_instance = (await SymbolORM.get_list(db=db, symbol_names=[symbol], broker_name=broker))[0]
        await SymbolORM.update(db, symbol_instance.id, rate=last_price) # type: ignore
