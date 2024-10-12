from datetime import datetime
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound, IntegrityError
from fastapi import APIRouter, Depends, HTTPException

from core.db import get_db
from routers import check_token
from models.user import UserORM
from models.order import OrderORM
from models.broker import BrokerORM
from models.symbol import SymbolORM

router = APIRouter(
    prefix="/trade",
    tags=["trade"],
)


@router.get("/orders")
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
    return result
