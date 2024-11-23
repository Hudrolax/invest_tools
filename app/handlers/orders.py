from decimal import Decimal
from datetime import datetime
import logging

from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import sessionmanager
from brokers.bybit import BYBIT_MARKET_TYPE_BROKER, BybitBroker

from models.broker import BrokerORM
from models.symbol import SymbolORM
from models.order import OrderORM
from utils import log_error_with_traceback

logger = logging.getLogger(__name__)


async def create_refresh_orders_in_db(
    db: AsyncSession,
    orders: list[dict],
    broker: BybitBroker,
    symbol: str,
) -> None:
    broker_instance = await BrokerORM.get_by_name(db, name=broker)
    try:
        symbol_instance = await SymbolORM.get_by_name_and_broker(db, name=symbol.upper(), broker_name=broker)
    except NoResultFound:
        symbol_instance = await SymbolORM.get_or_create(db, symbol, broker_instance.id)

    await SymbolORM.update(db, id=symbol_instance.id, active_wss=True)

    for order in orders:
        kwargs = dict(
            price=Decimal(order["price"]),
            qty=Decimal(order["qty"]),
            order_status=order["orderStatus"],
            cancel_type=order.get("cancelType"),
            avg_price=(Decimal(order.get("avgPrice", 0)) if order.get("avgPrice") else None),
            leaves_qty=Decimal(order["leavesQty"]),
            leaves_value=Decimal(order["leavesValue"]),
            cum_exec_qty=Decimal(order["cumExecQty"]),
            cum_exec_value=Decimal(order["cumExecValue"]),
            cum_exec_fee=Decimal(order["cumExecFee"]),
            trigger_price=(Decimal(order.get("triggerPrice", 0)) if order.get("triggerPrice") else None),
            take_profit=(Decimal(order.get("takeProfit", 0)) if order.get("takeProfit") else None),
            stop_loss=(Decimal(order.get("stopLoss", 0)) if order.get("stopLoss") else None),
            updated_time=(
                datetime.fromtimestamp(int(order["updatedTime"]) / 1000) if order.get("updatedTime") else None
            ),
        )
        try:
            order_obj = await OrderORM.get_by_broker_order_id(db, order["orderId"])
            await OrderORM.update(db, id=order_obj.id, **kwargs)
        except NoResultFound:
            await OrderORM.create(
                db,
                user_id=1,
                symbol_id=symbol_instance.id,
                broker_order_id=order["orderId"],
                side=order["side"],
                create_type=order.get("createType"),
                order_type=order.get("orderType"),
                stop_order_type=order.get("stopOrderType"),
                tpsl_mode=order.get("tpslMode"),
                last_price_on_created=Decimal(order["lastPriceOnCreated"]),
                created_time=datetime.fromtimestamp(int(order["createdTime"]) / 1000),
                **kwargs,
            )


async def handle_orders(
    orders_data: dict,
) -> None:
    if not orders_data.get("data"):
        return
    orders_all = orders_data["data"]
    categories = set([order["category"] for order in orders_all])
    symbols = set([order["symbol"] for order in orders_all])

    try:
        async with sessionmanager.session() as db:
            for category in categories:
                for symbol in symbols:
                    orders = [order for order in orders_all if order["category"] == category and order["symbol"] == symbol]
                    await create_refresh_orders_in_db(
                        db,
                        orders,
                        broker=BYBIT_MARKET_TYPE_BROKER[category],  # type: ignore
                        symbol=symbol,
                    )
    except Exception as ex:
        log_error_with_traceback(logger, ex)
        raise

    logger.info('orders updated with ws')
