from datetime import datetime

from sqlalchemy.exc import NoResultFound

from brokers.exceptions import GetPositionsError, CloseOrderError
from core.db import get_db
from fastapi import APIRouter, Depends, HTTPException
from models.broker import BrokerORM
from models.order import OrderORM
from models.symbol import SymbolORM
from models.user import UserORM
from models.position import PositionORM
from pydantic import BaseModel, validator
from routers import check_token, format_decimal, format_date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from brokers.bybit.bybit_api import cancel_order
from brokers.bybit import BYBIT_BROKERS, BybitBroker

router = APIRouter(
    prefix="/trade",
    tags=["trade"],
)


class PositionBase(BaseModel):
    symbol: str
    leverage: str
    entryPrice: str
    liqPrice: str
    takeProfit: str
    positionValue: str
    unrealisedPnl: str
    markPrice: str
    cumRealisedPnl: str
    createdTime: str
    updatedTime: str
    side: str
    curRealisedPnl: str
    size: str
    stopLoss: str

    @validator(
        "leverage", "entryPrice", "liqPrice", "takeProfit", "positionValue",
        "unrealisedPnl", "markPrice", "cumRealisedPnl", "curRealisedPnl", "size", "stopLoss", pre=True
    )
    def format_decimal_fields(cls, value):
        return format_decimal(value)

    @validator("createdTime", "updatedTime", pre=True)
    def format_date_field(cls, value):
        return str(format_date(value))


class PositionInstance(PositionBase):
    id: int


class OrderBase(BaseModel):
    side: str
    strategy_id: str | None = None
    order_status: str
    order_type: str
    price: str
    qty: str
    cum_exec_qty: str
    cum_exec_fee: str
    take_profit: str | None = None
    stop_loss: str | None = None
    created_time: int

    @validator(
        "price", "qty", "cum_exec_qty", "cum_exec_fee", "take_profit", "stop_loss", pre=True
    )
    def format_decimal_fields(cls, value):
        return format_decimal(value)

    @validator("created_time", pre=True)
    def format_date_field(cls, value):
        return format_date(value)


class OrderInstance(OrderBase):
    id: int


class CancelOrder(BaseModel):
    order_id: int
    broker: BybitBroker
    symbol: str


@router.get("/order", response_model=list[OrderInstance])
async def api_get_orders(
    startTime: int,
    broker: str,
    symbol: str,
    db: AsyncSession = Depends(get_db),
    user: UserORM = Depends(check_token),
):
    query = (
        select(
            OrderORM.id,
            OrderORM.side,
            OrderORM.strategy_id,
            OrderORM.order_status,
            OrderORM.order_type,
            OrderORM.price,
            OrderORM.qty,
            OrderORM.cum_exec_qty,
            OrderORM.cum_exec_fee,
            OrderORM.take_profit,
            OrderORM.stop_loss,
            OrderORM.created_time,
        )
        .select_from(OrderORM)
        .join(BrokerORM, (BrokerORM.id == OrderORM.broker_id) & (BrokerORM.name == broker))
        .join(SymbolORM, (SymbolORM.id == OrderORM.symbol_id) & (SymbolORM.name == symbol))
        .where(
            (OrderORM.user_id == user.id)
            & (OrderORM.created_time >= datetime.fromtimestamp(startTime))
            & (OrderORM.order_status != "Cancelled")
        )
    )
    result = (await db.execute(query)).mappings().all()
    result = [OrderInstance(**order) for order in result]
    return result


@router.post("/order/cancel", response_model=bool)
async def api_cancel_orders(
    payload: CancelOrder,
    db: AsyncSession = Depends(get_db),
    user: UserORM = Depends(check_token),
) -> bool:
    try:
        order = await OrderORM.get_by_id_and_user(db, id=payload.order_id, user_id=user.id)

        if payload.broker in BYBIT_BROKERS:
            try:
                result = await cancel_order(
                    orderId=str(order.broker_order_id), broker=payload.broker, symbol=payload.symbol
                )
                print(result)
                return result
            except CloseOrderError as ex:
                if 'order not exists or too late to cancel' in str(ex):
                    await OrderORM.delete(db, order.id)
                    return True
                raise

        else:
            raise HTTPException(422, f"Wrong broker {payload.broker}")

    except NoResultFound:
        raise HTTPException(403, "Wrong order_id or user_id!")



@router.get("/position", response_model=PositionInstance)
async def api_get_posiotions(
    broker: BybitBroker,
    symbol: str,
    db: AsyncSession = Depends(get_db),
    user: UserORM = Depends(check_token),
) -> PositionInstance:
    try:
        position = await PositionORM.get_by_broker_symbol(db, broker, symbol, user.id)

        return PositionInstance(
            id=position.id,
            symbol=symbol,
            leverage=position.leverage,
            entryPrice=position.entry_price,
            liqPrice=position.liq_price,
            takeProfit=position.take_profit,
            positionValue=position.position_value,
            unrealisedPnl=position.unrealised_pnl,
            markPrice=position.mark_price,
            cumRealisedPnl=position.cum_realised_pnl,
            createdTime=position.created_time,
            updatedTime=position.updated_time,
            side=position.side,
            curRealisedPnl=position.cur_realised_pnl,
            size=position.size,
            stopLoss=position.stop_loss,
        )
    except GetPositionsError:
        raise HTTPException(500, "broker not available")
