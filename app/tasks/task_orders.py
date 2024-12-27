import asyncio
import logging

from sqlalchemy.exc import NoResultFound
from sqlalchemy import delete, select
from decimal import Decimal
from datetime import datetime, timedelta

from brokers.bybit import BybitBroker, BYBIT_BROKERS
from brokers.bybit.bybit_api import (
    get_orders,
    get_order_history,
)
from models.order import OrderORM
from models.broker import BrokerORM
from models.symbol import SymbolORM
from core.db import DatabaseSessionManager
from utils import async_traceback_errors, log_error_with_traceback

logger = logging.getLogger(__name__)


async def fetch_orders_and_history(broker_name: BybitBroker, symbol_name: str) -> list[dict]:
    orders, order_history = await asyncio.gather(
        get_orders(broker_name, symbol_name),
        get_order_history(broker_name, symbol_name),
    )
    return orders + order_history


async def grab_old_orders(broker_name: BybitBroker, symbol_name: str) -> list[dict]:
    """
    Retrieve historical orders for a given broker and symbol starting from January 1, 2024.

    Args:
        broker_name (BybitBroker): The broker from which to retrieve order history.
        symbol_name (str): The symbol for which to retrieve order history.

    Returns:
        list[dict]: A list of dictionaries containing order details.
    """
    start_date = int(datetime(2024, 1, 1).timestamp() * 1000)
    order_list = []
    while True:
        orders = await get_order_history(broker_name, symbol_name, startTime=start_date)
        order_list.extend(orders)
        start_date += int(timedelta(weeks=1).total_seconds() * 1000)
        if start_date >= datetime.now().timestamp():
            return order_list
        logger.info(".")


@async_traceback_errors(logger=logger)
async def task_remove_old_orders(
    stop_event: asyncio.Event,
    sessionmaker: DatabaseSessionManager,
) -> None:
    logger = logging.getLogger("task_remove_old_orders")
    logger.info(f"start task: {logger.name}")
    while not stop_event.is_set():
        try:
            # delete old insignificant orders
            async with sessionmaker.session() as db:
                await db.execute(
                    delete(OrderORM).where(
                        (OrderORM.updated_time < datetime.now() - timedelta(days=7))
                        & (
                            (OrderORM.order_status == "Untriggered")
                            | (OrderORM.order_status == "Rejected")
                            | (OrderORM.order_status == "Cancelled")
                            | (OrderORM.order_status == "Deactivated")
                            | (OrderORM.order_status == "Triggered")
                        )
                    )
                )

            # get actual openned orders for checking
            async with sessionmaker.session() as db:
                query = (
                    select(
                        OrderORM.id,
                        OrderORM.broker_order_id,
                        BrokerORM.name.label("broker_name"),
                    )
                    .where((OrderORM.order_status == "New") | (OrderORM.order_status == "PartiallyFilled"))
                    .join(SymbolORM, SymbolORM.id == OrderORM.symbol_id)
                    .join(BrokerORM, BrokerORM.id == SymbolORM.broker_id)
                )
                actual_orders = (await db.execute(query)).mappings().all()

            for order in actual_orders:
                broker_orders = await get_orders(
                    broker=order["broker_name"],
                    orderId=order["broker_order_id"],
                )
                try:
                    async with sessionmaker.session() as db:
                        if broker_orders:
                            kwargs = dict(
                                price=Decimal(broker_orders[0]["price"]),
                                qty=Decimal(broker_orders[0]["qty"]),
                                order_status=broker_orders[0]["orderStatus"],
                                cancel_type=broker_orders[0].get("cancelType"),
                                avg_price=(
                                    Decimal(broker_orders[0].get("avgPrice", 0))
                                    if broker_orders[0].get("avgPrice")
                                    else None
                                ),
                                leaves_qty=Decimal(broker_orders[0]["leavesQty"]),
                                leaves_value=Decimal(broker_orders[0]["leavesValue"]),
                                cum_exec_qty=Decimal(broker_orders[0]["cumExecQty"]),
                                cum_exec_value=Decimal(broker_orders[0]["cumExecValue"]),
                                cum_exec_fee=Decimal(broker_orders[0]["cumExecFee"]),
                                trigger_price=(
                                    Decimal(broker_orders[0].get("triggerPrice", 0))
                                    if broker_orders[0].get("triggerPrice")
                                    else None
                                ),
                                take_profit=(
                                    Decimal(broker_orders[0].get("takeProfit", 0))
                                    if broker_orders[0].get("takeProfit")
                                    else None
                                ),
                                stop_loss=(
                                    Decimal(broker_orders[0].get("stopLoss", 0))
                                    if broker_orders[0].get("stopLoss")
                                    else None
                                ),
                                updated_time=(
                                    datetime.fromtimestamp(int(broker_orders[0]["updatedTime"]) / 1000)
                                    if broker_orders[0].get("updatedTime")
                                    else None
                                ),
                            )
                            await OrderORM.update(db, id=order["id"], **kwargs)
                            logger.info(f'order {order["id"]} updated')
                        else:
                            await db.execute(delete(OrderORM).where(OrderORM.id == order["id"]))
                            logger.info(f'order {order["id"]} deleted')
                except Exception as ex:
                    log_error_with_traceback(logger, ex)

            await asyncio.sleep(86400)
        except Exception as ex:
            logger.error(f"Error deleting old cancelled orders: {str(ex)}")
            await asyncio.sleep(300)


async def task_get_old_orders(
    stop_event: asyncio.Event,
    sessionmaker: DatabaseSessionManager,
) -> None:
    logger = logging.getLogger("task_get_old_orders")
    logger.info(f"start task: {logger.name}")
    while not stop_event.is_set():
        try:
            broker_symbol = []
            async with sessionmaker.session() as db:
                for broker in BYBIT_BROKERS:
                    symbols = (
                        (
                            await db.execute(
                                select(SymbolORM.name)
                                .select_from(SymbolORM)
                                .join(
                                    BrokerORM,
                                    (BrokerORM.id == SymbolORM.broker_id) & (BrokerORM.name == broker),
                                )
                                .where(SymbolORM.active_wss)
                            )
                        )
                        .mappings()
                        .all()
                    )
                    for symbol in symbols:
                        broker_symbol.append((broker, symbol["name"]))

            for broker_name, symbol_name in broker_symbol:
                await asyncio.sleep(0.2)
                async with sessionmaker.session() as db:
                    logging.info("try to grab old orders")
                    broker = await BrokerORM.get_by_name(db, broker_name)
                    symbol = await SymbolORM.get_by_name_and_broker(db, symbol_name, broker_name)

                orders = await grab_old_orders(broker_name, symbol_name)
                async with sessionmaker.session() as db:
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
                            trigger_price=(
                                Decimal(order.get("triggerPrice", 0)) if order.get("triggerPrice") else None
                            ),
                            take_profit=(Decimal(order.get("takeProfit", 0)) if order.get("takeProfit") else None),
                            stop_loss=(Decimal(order.get("stopLoss", 0)) if order.get("stopLoss") else None),
                            updated_time=(
                                datetime.fromtimestamp(int(order["updatedTime"]) / 1000)
                                if order.get("updatedTime")
                                else None
                            ),
                        )
                        await OrderORM.create(
                            db,
                            user_id=1,
                            symbol_id=symbol.id,
                            broker_order_id=order["orderId"],
                            side=order["side"],
                            create_type=order["createType"],
                            order_type=order.get("orderType"),
                            stop_order_type=order.get("stopOrderType"),
                            tpsl_mode=order.get("tpslMode"),
                            last_price_on_created=Decimal(order["lastPriceOnCreated"]),
                            created_time=datetime.fromtimestamp(int(order["createdTime"]) / 1000),
                            **kwargs,
                        )
                    logger.info(f"{len(orders)} old orders added")

            await asyncio.sleep(300)
        except Exception as ex:
            log_error_with_traceback(logger, ex)


@async_traceback_errors(logger=logger)
async def task_get_orders(
    stop_event: asyncio.Event,
    sessionmaker: DatabaseSessionManager,
) -> None:
    logger = logging.getLogger("task_get_orders")
    logger.info(f"start task: {logger.name}")

    while not stop_event.is_set():
        try:
            broker_symbol = []
            async with sessionmaker.session() as db:
                for broker in BYBIT_BROKERS:
                    symbols = (
                        (
                            await db.execute(
                                select(SymbolORM.name)
                                .select_from(SymbolORM)
                                .join(
                                    BrokerORM,
                                    (BrokerORM.id == SymbolORM.broker_id) & (BrokerORM.name == broker),
                                )
                                .where(SymbolORM.active_wss)
                            )
                        )
                        .mappings()
                        .all()
                    )
                    for symbol in symbols:
                        broker_symbol.append((broker, symbol["name"]))

            for broker_name, symbol_name in broker_symbol:
                async with sessionmaker.session() as db:
                    # get orders
                    # broker = await BrokerORM.get_by_name(db, broker_name)
                    query = (
                        select(SymbolORM.id)
                        .where(SymbolORM.name == symbol_name)
                        .join(BrokerORM, (BrokerORM.id == SymbolORM.broker_id) & (BrokerORM.name == broker_name))
                    )
                    symbol = (await db.execute(query)).mappings().first()
                    if not symbol:
                        raise ValueError(f'unexpected symbol {symbol_name} {broker_name}')

                orders = await fetch_orders_and_history(broker_name, symbol_name)
                for order in orders:
                    async with sessionmaker.session() as db:
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
                            trigger_price=(
                                Decimal(order.get("triggerPrice", 0)) if order.get("triggerPrice") else None
                            ),
                            take_profit=(Decimal(order.get("takeProfit", 0)) if order.get("takeProfit") else None),
                            stop_loss=(Decimal(order.get("stopLoss", 0)) if order.get("stopLoss") else None),
                            updated_time=(
                                datetime.fromtimestamp(int(order["updatedTime"]) / 1000)
                                if order.get("updatedTime")
                                else None
                            ),
                        )
                        try:
                            order_obj = await OrderORM.get_by_broker_order_id(db, order["orderId"])
                            await OrderORM.update(db, id=order_obj.id, **kwargs)
                        except NoResultFound:
                            await OrderORM.create(
                                db,
                                user_id=1,
                                symbol_id=symbol['id'],
                                broker_order_id=order["orderId"],
                                side=order["side"],
                                create_type=order["createType"],
                                order_type=order.get("orderType"),
                                stop_order_type=order.get("stopOrderType"),
                                tpsl_mode=order.get("tpslMode"),
                                last_price_on_created=Decimal(order["lastPriceOnCreated"]),
                                created_time=datetime.fromtimestamp(int(order["createdTime"]) / 1000),
                                **kwargs,
                            )

            await asyncio.sleep(120)
        except Exception as ex:
            log_error_with_traceback(logger, ex)
            await asyncio.sleep(120)
