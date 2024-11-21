from sqlalchemy import (
    Column,
    Integer,
    String,
    select,
    ForeignKey,
    DECIMAL,
    TEXT,
    TIMESTAMP,
)
from sqlalchemy.orm import relationship
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Self
from decimal import Decimal

from .base_object import BaseDBObject


class OrderORM(BaseDBObject):
    __tablename__ = "orders"  # type: ignore
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol_id = Column(Integer, ForeignKey("symbols.id", ondelete="CASCADE"), nullable=False, index=True)
    broker_order_id = Column(String, nullable=False, index=True)
    strategy_id = Column(String, nullable=True, index=True)
    price = Column(DECIMAL(precision=20, scale=8), nullable=False)
    qty = Column(DECIMAL(precision=20, scale=8), nullable=False)
    side = Column(String, nullable=False, index=True)
    order_status = Column(String, nullable=False, index=True)
    create_type = Column(String, nullable=False, index=True)
    cancel_type = Column(String, nullable=True, index=True)
    avg_price = Column(DECIMAL(precision=20, scale=8), nullable=True)
    leaves_qty = Column(DECIMAL(precision=20, scale=8), nullable=False, default=Decimal(0))
    leaves_value = Column(DECIMAL(precision=20, scale=8), nullable=False, default=Decimal(0))
    cum_exec_qty = Column(DECIMAL(precision=20, scale=8), nullable=False, default=Decimal(0))
    cum_exec_value = Column(DECIMAL(precision=20, scale=8), nullable=False, default=Decimal(0))
    cum_exec_fee = Column(DECIMAL(precision=20, scale=8), nullable=False, default=Decimal(0))
    order_type = Column(String, nullable=False, index=True)
    stop_order_type = Column(String, nullable=False, index=True)
    trigger_price = Column(DECIMAL(precision=20, scale=8), nullable=True)
    take_profit = Column(DECIMAL(precision=20, scale=8), nullable=True)
    stop_loss = Column(DECIMAL(precision=20, scale=8), nullable=True)
    tpsl_mode = Column(String, nullable=True, index=True)
    last_price_on_created = Column(DECIMAL(precision=20, scale=8), nullable=False)
    created_time = Column(TIMESTAMP, nullable=False, index=True)
    updated_time = Column(TIMESTAMP, nullable=True, index=True)
    comment = Column(TEXT, nullable=True)

    symbol = relationship("SymbolORM", back_populates="orders")
    user = relationship("UserORM", back_populates="orders")

    def __str__(self) -> str:
        return f"order: user {self.user_id} {self.order_status} {self.side} {self.order_type} price {self.price} qty {self.qty}"

    @classmethod
    async def get_by_id_and_user(cls, db: AsyncSession, id: int | Column[int], user_id: int | Column[int]) -> Self:
        result = (await db.scalars(select(cls).where((cls.id == id) & (cls.user_id == user_id)))).first()
        if not result:
            raise NoResultFound
        return result

    @classmethod
    async def get_by_broker_order_id(cls, db: AsyncSession, broker_order_id: str) -> Self:
        result = (await db.scalars(select(cls).where(cls.broker_order_id == broker_order_id))).first()
        if not result:
            raise NoResultFound
        return result
