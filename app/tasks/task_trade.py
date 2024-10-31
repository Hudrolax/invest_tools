import asyncio
import logging

from sqlalchemy.exc import NoResultFound
from sqlalchemy import delete, select
from decimal import Decimal
from datetime import datetime, timedelta

from brokers.bybit.bybit_api import get_orders, get_order_history, get_position_info
from models.order import OrderORM
from models.broker import BrokerORM
from models.symbol import SymbolORM
from core.db import DatabaseSessionManager
from utils import async_traceback_errors
from handlers.positions import refresh_positions_in_db

logger = logging.getLogger(__name__)


async def fetch_orders_and_history() -> list[dict]:
    orders, order_history = await asyncio.gather(
        get_orders("Bybit-inverse", "BTCUSD"),
        get_order_history("Bybit-inverse", "BTCUSD"),
    )
    return orders + order_history


async def grab_old_orders() -> list[dict]:
    start_date = int(datetime(2024, 1, 1).timestamp() * 1000)
    order_list = []
    while True:
        orders = await get_order_history("Bybit-inverse", "BTCUSD", startTime=start_date)
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
            async with sessionmaker.session() as db:
                await db.execute(
                    delete(OrderORM).where(
                        (OrderORM.updated_time < datetime.now() - timedelta(days=30))
                        & (OrderORM.order_status == "Cancelled")
                    )
                )

            await asyncio.sleep(86400)
        except Exception as ex:
            logger.error(f"Error deleting old cancelled orders: {str(ex)}")


@async_traceback_errors(logger=logger)
async def task_get_orders(
    stop_event: asyncio.Event,
    sessionmaker: DatabaseSessionManager,
) -> None:
    logger = logging.getLogger("task_get_orders")
    logger.info(f"start task: {logger.name}")
    try:
        async with sessionmaker.session() as db:
            logging.info("try to grab old orders")
            broker = await BrokerORM.get_by_name(db, "Bybit-inverse")
            symbol = await SymbolORM.get_by_name_and_broker(db, "BTCUSD", "Bybit-inverse")

            orders = await grab_old_orders()
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
                    **kwargs,
                )
            logger.info(f"{len(orders)} old orders added")
    except Exception as ex:
        logger.critical(f"Error when grabbing old orders: {str(ex)}")

    while not stop_event.is_set():
        try:
            async with sessionmaker.session() as db:
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
                            **kwargs,
                        )

            await asyncio.sleep(60)
        except Exception as ex:
            logger.critical(str(ex))
            await asyncio.sleep(10)


@async_traceback_errors(logger=logger)
async def task_get_positions(
    stop_event: asyncio.Event,
    sessionmaker: DatabaseSessionManager,
) -> None:
    """
    Get positions once in 60 second. Base positions refresh handler working with WebSocket
    """
    logger = logging.getLogger("task_get_positons")
    logger.info(f"start task: {logger.name}")
    while not stop_event.is_set():
        try:
            async with sessionmaker.session() as db:
                for broker in ["Bybit_perpetual", "Bybit-inverse"]:
                    broker_symbols = (
                        (
                            await db.execute(
                                select(SymbolORM.name)
                                .select_from(SymbolORM)
                                .join(BrokerORM, (BrokerORM.id == SymbolORM.broker_id) & (BrokerORM.name == broker))
                            )
                        )
                        .mappings()
                        .all()
                    )
                    for symbol in broker_symbols:
                        positions: list[dict] = await get_position_info(broker, symbol["name"])  # type: ignore
                        positions = [pos for pos in positions if pos["positionValue"] != ""]
                        await refresh_positions_in_db(db, positions, broker, symbol["name"])  # type: ignore
                    await asyncio.sleep(1)

            await asyncio.sleep(60)
        except Exception as ex:
            logger.error(f"Error in task_get_positions: {str(ex)}")
            await asyncio.sleep(10)
