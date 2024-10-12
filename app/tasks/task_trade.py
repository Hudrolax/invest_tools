import asyncio
import logging

from sqlalchemy.exc import NoResultFound
from decimal import Decimal
from datetime import datetime, timedelta

from brokers.bybit.bybit_api import get_orders, get_order_history
from models.order import OrderORM
from models.broker import BrokerORM
from models.symbol import SymbolORM
from core.db import DatabaseSessionManager
from utils import async_traceback_errors

logger = logging.getLogger(__name__)

async def fetch_orders_and_history() -> list[dict]:
    orders, order_history = await asyncio.gather(
        get_orders("inverse", "BTCUSD"),
        get_order_history("inverse", "BTCUSD"),
    )
    return orders + order_history

async def grab_old_orders() -> list[dict]:
    start_date = int(datetime(2024, 1, 1).timestamp() * 1000)
    order_list = []
    while True:
        orders = await get_order_history("inverse", "BTCUSD", startTime=start_date)
        order_list.extend(orders)
        start_date += int(timedelta(weeks=1).total_seconds() * 1000)
        if start_date >= datetime.now().timestamp():
            return order_list
        logger.info('.')

@async_traceback_errors(logger=logger)
async def task_get_orders(
    stop_event: asyncio.Event,
    sessionmaker: DatabaseSessionManager,
) -> None:
    async with sessionmaker.session() as db:
        try:
            print('try to grab old orders')
            broker = await BrokerORM.get_by_name(db, "Bybit-inverse")
            symbol = await SymbolORM.get_by_name_and_broker(db, "BTCUSD", "Bybit-inverse")
            orders = await grab_old_orders()
            for order in orders:
                kwargs = dict(
                    price=Decimal(order["price"]),
                    qty=Decimal(order["qty"]),
                    order_status=order["orderStatus"],
                    cancel_type=order.get("cancelType"),
                    avg_price=(
                        Decimal(order.get("avgPrice", 0)) if order.get("avgPrice") else None
                    ),
                    leaves_qty=Decimal(order["leavesQty"]),
                    leaves_value=Decimal(order["leavesValue"]),
                    cum_exec_qty=Decimal(order["cumExecQty"]),
                    cum_exec_value=Decimal(order["cumExecValue"]),
                    cum_exec_fee=Decimal(order["cumExecFee"]),
                    trigger_price=(
                        Decimal(order.get("triggerPrice", 0))
                        if order.get("triggerPrice")
                        else None
                    ),
                    take_profit=(
                        Decimal(order.get("takeProfit", 0)) if order.get("takeProfit") else None
                    ),
                    stop_loss=(
                        Decimal(order.get("stopLoss", 0)) if order.get("stopLoss") else None
                    ),
                    updated_time=(
                        datetime.fromtimestamp(int(order["updatedTime"]) / 1000)
                        if order.get("updatedTime")
                        else None
                    ),
                )
                await OrderORM.create(
                    db,
                    user_id=1,
                    broker_id=broker.id,
                    symbol_id=symbol.id,
                    broker_order_id=order["orderId"],
                    side=order["side"],
                    create_type=order["createType"],
                    order_type=order.get("orderType"),
                    stop_order_type=order.get("stopOrderType"),
                    tpsl_mode=order.get("tpslMode"),
                    last_price_on_created=Decimal(order["lastPriceOnCreated"]),
                    created_time=datetime.fromtimestamp(int(order["createdTime"]) / 1000),
                    **kwargs
                )
            print(f"{len(orders)} old orders added")
        except Exception as ex:
            logger.error(f"Error when grabbing old orders: {str(ex)}")

    while not stop_event.is_set():
        async with sessionmaker.session() as db:
            try: 
                # get orders
                broker = await BrokerORM.get_by_name(db, "Bybit-inverse")
                symbol = await SymbolORM.get_by_name_and_broker(db, "BTCUSD", "Bybit-inverse")
                orders = await fetch_orders_and_history()

                for order in orders:
                    kwargs = dict(
                        price=Decimal(order["price"]),
                        qty=Decimal(order["qty"]),
                        order_status=order["orderStatus"],
                        cancel_type=order.get("cancelType"),
                        avg_price=(
                            Decimal(order.get("avgPrice", 0)) if order.get("avgPrice") else None
                        ),
                        leaves_qty=Decimal(order["leavesQty"]),
                        leaves_value=Decimal(order["leavesValue"]),
                        cum_exec_qty=Decimal(order["cumExecQty"]),
                        cum_exec_value=Decimal(order["cumExecValue"]),
                        cum_exec_fee=Decimal(order["cumExecFee"]),
                        trigger_price=(
                            Decimal(order.get("triggerPrice", 0))
                            if order.get("triggerPrice")
                            else None
                        ),
                        take_profit=(
                            Decimal(order.get("takeProfit", 0)) if order.get("takeProfit") else None
                        ),
                        stop_loss=(
                            Decimal(order.get("stopLoss", 0)) if order.get("stopLoss") else None
                        ),
                        updated_time=(
                            datetime.fromtimestamp(int(order["updatedTime"]) / 1000)
                            if order.get("updatedTime")
                            else None
                        ),
                    )
                    try:
                        order_obj = await OrderORM.get_by_broker_order_id(db, order["orderId"])
                        await OrderORM.update(
                            db,
                            id=order_obj.id,
                            **kwargs
                        )
                    except NoResultFound:
                        await OrderORM.create(
                            db,
                            user_id=1,
                            broker_id=broker.id,
                            symbol_id=symbol.id,
                            broker_order_id=order["orderId"],
                            side=order["side"],
                            create_type=order["createType"],
                            order_type=order.get("orderType"),
                            stop_order_type=order.get("stopOrderType"),
                            tpsl_mode=order.get("tpslMode"),
                            last_price_on_created=Decimal(order["lastPriceOnCreated"]),
                            created_time=datetime.fromtimestamp(int(order["createdTime"]) / 1000),
                            **kwargs
                        )

                await asyncio.sleep(3)
            except Exception as ex:
                logger.critical(str(ex))
                await asyncio.sleep(10)
