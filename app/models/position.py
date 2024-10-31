from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DECIMAL,
    TEXT,
    TIMESTAMP,
    select,
)
from sqlalchemy.orm import relationship
from decimal import Decimal
from .base_object import BaseDBObject
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound, IntegrityError, OperationalError
from models.broker import BrokerORM
from models.symbol import SymbolORM
from models.user import UserORM
from typing import Sequence


class PositionORM(BaseDBObject):
    __tablename__ = "positions"  # type: ignore
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    broker_id = Column(Integer, ForeignKey("brokers.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol_id = Column(Integer, ForeignKey("symbols.id", ondelete="CASCADE"), nullable=False, index=True)
    side = Column(String, nullable=False, index=True)
    size = Column(DECIMAL(precision=20, scale=8), nullable=False)
    position_value = Column(DECIMAL(precision=20, scale=8), nullable=False)
    mark_price = Column(DECIMAL(precision=20, scale=8), nullable=False)
    entry_price = Column(DECIMAL(precision=20, scale=8), nullable=False)
    leverage = Column(DECIMAL(precision=20, scale=8), nullable=True)
    position_balance = Column(DECIMAL(precision=20, scale=8), nullable=True)
    liq_price = Column(DECIMAL(precision=20, scale=8), nullable=False, default=Decimal(0))
    take_profit = Column(DECIMAL(precision=20, scale=8), nullable=True)
    stop_loss = Column(DECIMAL(precision=20, scale=8), nullable=True)
    unrealised_pnl = Column(DECIMAL(precision=20, scale=8), nullable=False)
    cur_realised_pnl = Column(DECIMAL(precision=20, scale=8), nullable=False)
    cum_realised_pnl = Column(DECIMAL(precision=20, scale=8), nullable=False)
    position_status = Column(String, nullable=False, index=True)
    created_time = Column(TIMESTAMP, nullable=False, index=True)
    updated_time = Column(TIMESTAMP, nullable=True, index=True)
    comment = Column(TEXT, nullable=True)

    broker = relationship("BrokerORM", back_populates="positions")
    symbol = relationship("SymbolORM", back_populates="positions")
    user = relationship("UserORM", back_populates="positions")

    def __str__(self) -> str:
        return f"position: user {self.user_id} broker {self.broker_id} {self.side} pnl {self.cum_realised_pnl}"

    @classmethod
    async def get_by_broker_symbol(
        cls,
        db: AsyncSession,
        broker: str | Column[str],
        symbol: str | Column[str],
        user_id: int | Column[int],
    ) -> 'BaseDBObject':
        result = (await db.execute(
            select(cls)
            .join(BrokerORM, BrokerORM.id == cls.broker_id)
            .join(SymbolORM, SymbolORM.id == cls.symbol_id)
            .where((BrokerORM.name == broker) & (SymbolORM.name == symbol) & (cls.user_id == user_id))
        )).scalars().all()
        if not result:
            raise NoResultFound
        if len(result) > 1:
            raise ValueError(f'Найдено больше одной позиции для брокера {broker} и символа {symbol}')
        return result[0]
