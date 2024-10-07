from decimal import Decimal
from datetime import datetime
import logging

from core.db import sessionmanager
from brokers.binance import BinanceBroker
from brokers.bybit import BybitBroker

from models.alert import AlertORM

logger = logging.getLogger(__name__)

async def handle_alerts(
    broker: BinanceBroker | BybitBroker,
    symbol: str,
    last_price: Decimal | str | int | float,
) -> None:
    last_price = last_price if isinstance(last_price, Decimal) else Decimal(last_price)

    async with sessionmanager.session() as db:
        alerts = await AlertORM.get_filtered_alerts_unauthorized(
            db,
            broker_name=broker,
            symbol_name=symbol,
            is_triggered=False,
            is_active=True,
            is_sent=False,
        )
        for alert in alerts:
            above_trigger: bool = alert.trigger == 'above' and last_price >= alert.price # type: ignore
            below_trigger: bool = alert.trigger == 'below' and last_price <= alert.price # type: ignore
            if above_trigger or below_trigger:
                await AlertORM.update(db, id=alert.id, triggered_at=datetime.now()) # type: ignore
