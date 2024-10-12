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
from sqlalchemy.exc import NoResultFound, IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Self
from decimal import Decimal

from core.db import Base


class OrderORM(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    broker_id = Column(Integer, ForeignKey("brokers.id", ondelete="CASCADE"), nullable=False)
    symbol_id = Column(Integer, ForeignKey("symbols.id", ondelete="CASCADE"), nullable=False)
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

    broker = relationship("BrokerORM", back_populates="orders")
    symbol = relationship("SymbolORM", back_populates="orders")
    user = relationship("UserORM", back_populates="orders")

    def __str__(self) -> str:
        return f"user {self.user_id} broker {self.broker_id} {self.order_status} {self.side} {self.order_type} price {self.price} qty {self.qty}"

    @classmethod
    async def create(cls, db: AsyncSession, **kwargs) -> Self:
        try:
            transaction = cls(**kwargs)
            db.add(transaction)
            await db.flush()
        except IntegrityError:
            await db.rollback()
            raise
        return transaction

    @classmethod
    async def update(cls, db: AsyncSession, id: int | Column[int], **kwargs) -> Self:
        try:
            # попытаться получить существующую запись
            existing_entry = await db.get(cls, id)
            if not existing_entry:
                raise NoResultFound

            # обновление полей записи
            for attr, value in kwargs.items():
                setattr(existing_entry, attr, value)

            await db.flush()
        except IntegrityError:
            await db.rollback()
            raise
        return existing_entry

    @classmethod
    async def delete(cls, db: AsyncSession, id: int) -> bool:
        try:
            # попытаться получить существующую запись
            existing_entry = await db.get(cls, id)
            if not existing_entry:
                raise NoResultFound

            # удалить запись из БД
            await db.delete(existing_entry)
            await db.flush()
            return True
        except (IntegrityError, OperationalError):
            await db.rollback()
            raise

    @classmethod
    async def get_by_id(cls, db: AsyncSession, id: int) -> Self:
        result = (await db.scalars(select(cls).where(cls.id == id))).first()
        if not result:
            raise NoResultFound
        return result

    @classmethod
    async def get_by_broker_order_id(cls, db: AsyncSession, broker_order_id: str) -> Self:
        result = (await db.scalars(select(cls).where(cls.broker_order_id == broker_order_id))).first()
        if not result:
            raise NoResultFound
        return result
