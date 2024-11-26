from decimal import Decimal
from datetime import datetime
import logging
from sqlalchemy import select

from models.symbol import SymbolORM
from models.user import UserORM
from models.broker import BrokerORM
from core.db import sessionmanager
from brokers.binance import BinanceBroker
from brokers.bybit import BybitBroker
from models.alert import AlertORM
from alert_bot_connector.connector import send_alert

logger = logging.getLogger(__name__)


async def handle_alerts(
    broker: BinanceBroker | BybitBroker,
    symbol: str,
    last_price: Decimal | str | int | float,
) -> None:
    _last_price: Decimal = (
        last_price if isinstance(last_price, Decimal) else Decimal(last_price)
    )

    async with sessionmanager.session() as db:
        query = (
            select(
                AlertORM.id.label('id'),
                AlertORM.trigger.label('trigger'),
                AlertORM.price.label('price'),
                AlertORM.comment.label('comment'),
                UserORM.username.label('username'),
                UserORM.telegram_id.label('telegram_id'),
            )
            .select_from(AlertORM)
            .join(
                SymbolORM,
                (SymbolORM.id == AlertORM.symbol_id) & (SymbolORM.name == symbol),
            )
            .join(
                BrokerORM,
                (BrokerORM.id == SymbolORM.broker_id) & (BrokerORM.name == broker),
            )
            .join(
                UserORM,
                (UserORM.id == AlertORM.user_id),
            )
            .where(
                (AlertORM.triggered_at.is_(None))
                & (AlertORM.is_active)
                & (AlertORM.is_sent == False)
            )
        )
        results = (await db.execute(query)).mappings().all()
        for record in results:
            above_trigger = bool(
                record['trigger'] == "above" and _last_price >= record['price']
            )
            below_trigger = bool(
                record['trigger'] == "below" and _last_price <= record['price']
            )
            if above_trigger or below_trigger:
                try:
                    trigger = "выше"
                    if below_trigger:
                        trigger = "ниже"
                    text = f"{symbol} {trigger} {record['price']}"
                    if record['comment']:
                        text += f' {record['comment']}'
                    await send_alert(
                        chat_id=record['telegram_id'],
                        text=text,
                    )
                    logger.info(f"Price alert {symbol} sent to {record['username']}")
                    await AlertORM.update(
                        db, id=record['id'], triggered_at=datetime.now(),
                        is_sent=True, is_active=False,
                    )
                except Exception as ex:
                    logger.error(str(ex))
