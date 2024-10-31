from sqlalchemy import (
    Column,
    Integer,
    String,
    select,
    ForeignKey,
    UniqueConstraint,
    DECIMAL,
    or_,
    func,
    TIMESTAMP,
)
from sqlalchemy.orm import relationship, aliased, joinedload
from sqlalchemy.exc import NoResultFound, IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Self, Sequence
from decimal import Decimal

from .base_object import BaseDBObject
from models.broker import BrokerORM


class SymbolORM(BaseDBObject):
    __tablename__ = "symbols"  # type: ignore
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    broker_id = Column(Integer, ForeignKey("brokers.id", ondelete="CASCADE"), nullable=False)
    rate = Column(DECIMAL(precision=20, scale=8), default=Decimal(1))
    last_update_time = Column(TIMESTAMP, nullable=True)
    __table_args__ = (UniqueConstraint("name", "broker_id", name="_symbol_name_broker_id_uc"),)

    broker = relationship("BrokerORM", back_populates="symbols")
    alerts = relationship("AlertORM", back_populates="symbol", cascade="all, delete")
    lines = relationship("LineORM", back_populates="symbol", cascade="all, delete")
    orders = relationship("OrderORM", back_populates="symbol", cascade="all, delete")
    positions = relationship("PositionORM", back_populates="symbol", cascade="all, delete")

    def __str__(self) -> str:
        return f"{self.name}"

    async def delete_self(self, db: AsyncSession) -> bool:
        return await SymbolORM.delete(db, self.id)  # type: ignore


    @classmethod
    async def get_by_name(cls, db: AsyncSession, name: str) -> 'SymbolORM':
        result = (await db.scalars(select(cls).where(cls.name == name))).first()
        if not result:
            raise NoResultFound(f'symbol with name {name} not found')
        return result

    @classmethod
    async def get_by_name_and_broker(cls, db: AsyncSession, name: str, broker_name: str | Column[str]) -> 'SymbolORM':
        result = (
            await db.scalars(
                select(cls).join(BrokerORM, BrokerORM.name == broker_name).where(cls.name == name)
            )
        ).first()
        if not result:
            raise NoResultFound(f'symbol with name {name} not found for broker {broker_name}')
        return result

    @classmethod
    async def get_or_create(cls, db: AsyncSession, name: str, broker_id: int) -> 'SymbolORM':
        result = (
            await db.scalars(select(cls).where(cls.name == name, cls.broker_id == broker_id))
        ).first()
        if not result:
            result = await cls.create(db, name=name, broker_id=broker_id)
        return result

    @classmethod
    async def get_all(cls, db: AsyncSession) -> Sequence['SymbolORM']:
        result = await db.execute(
            select(cls).options(joinedload(cls.broker)).order_by(cls.id.asc())
        )
        return result.scalars().all()

    @classmethod
    async def get_list(cls, db: AsyncSession, **kwargs) -> list["SymbolORM"]:
        conditions = []

        # Проверка идентификаторов
        if "symbol_ids" in kwargs and kwargs["symbol_ids"] is not None:
            conditions.append(cls.id.in_(kwargs["symbol_ids"]))

        # Проверка названий символов
        if "symbol_names" in kwargs and kwargs["symbol_names"] is not None:
            conditions.append(cls.name.in_([name.upper() for name in kwargs["symbol_names"]]))

        # Подготовка запроса с условием для соединения
        query = select(cls).join(BrokerORM, cls.broker_id == BrokerORM.id, isouter=True)

        # Проверка названия брокера
        if "broker_name" in kwargs and kwargs["broker_name"] is not None:
            broker_alias = aliased(BrokerORM)
            query = query.join(broker_alias, cls.broker_id == broker_alias.id)
            conditions.append(broker_alias.name == kwargs["broker_name"])

        # Проверка названий валют
        if "currency_names" in kwargs and kwargs["currency_names"] is not None:
            currency_conditions = []
            for currency_name in kwargs["currency_names"]:
                upper_currency_name = currency_name.upper()
                currency_conditions.append(func.upper(cls.name).like(f"{upper_currency_name}%"))
                currency_conditions.append(func.upper(cls.name).like(f"%{upper_currency_name}"))
            conditions.append(or_(*currency_conditions))

        if conditions:
            query = query.where(*conditions)

        result = await db.scalars(query)
        return list(result.all())
