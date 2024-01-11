from sqlalchemy import Column, Integer, String, select, ForeignKey, UniqueConstraint, DECIMAL, or_, func
from sqlalchemy.orm import relationship, aliased, joinedload
from sqlalchemy.exc import NoResultFound, IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Self, Sequence
from decimal import Decimal

from core.db import Base
from models.broker import BrokerORM


class SymbolORM(Base):
    __tablename__ = "symbols"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    broker_id = Column(Integer, ForeignKey('brokers.id', ondelete='CASCADE'), nullable=False)
    rate = Column(DECIMAL(precision=20, scale=8), default=Decimal(1))
    __table_args__ = (
        UniqueConstraint('name', 'broker_id', name='_symbol_name_broker_id_uc'),
    )

    broker = relationship('BrokerORM', back_populates='symbols')
    alerts = relationship('AlertORM', back_populates='symbol', cascade="all, delete")

    def __str__(self) -> str:
        return f'{self.name}'
    
    async def delete_self(self, db: AsyncSession) -> bool:
        return await SymbolORM.delete(db, self.id) # type: ignore

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
    async def update(cls, db: AsyncSession, id: int, **kwargs) -> Self:
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
    async def get(cls, db: AsyncSession, id: int) -> Self:
        result = (await db.scalars(select(cls).where(cls.id == id))).first()
        if not result:
            raise NoResultFound
        return result

    @classmethod
    async def get_by_name(cls, db: AsyncSession, name: str) -> Self:
        result = (await db.scalars(select(cls).where(cls.name == name))).first()
        if not result:
            raise NoResultFound
        return result

    @classmethod
    async def get_or_create(cls, db: AsyncSession, name: str, broker_id: int) -> Self:
        result = (await db.scalars(select(cls).where(cls.name == name, cls.broker_id==broker_id))).first()
        if not result:
            result = await cls.create(db, name=name, broker_id=broker_id)
        return result

    @classmethod
    async def get_all(cls, db: AsyncSession) -> Sequence[Self]:
        result = await db.execute(
            select(cls).options(joinedload(cls.broker)).order_by(cls.id.asc())
        )
        return result.scalars().all()


    @classmethod
    async def get_list(cls, db: AsyncSession, **kwargs) -> list['SymbolORM']:
        conditions = []

        # Проверка идентификаторов
        if 'symbol_ids' in kwargs and kwargs['symbol_ids'] is not None:
            conditions.append(cls.id.in_(kwargs['symbol_ids']))

        # Проверка названий символов
        if 'symbol_names' in kwargs and kwargs['symbol_names'] is not None:
            conditions.append(cls.name.in_([name.upper() for name in kwargs['symbol_names']]))

        # Подготовка запроса с условием для соединения
        query = select(cls).join(BrokerORM, cls.broker_id == BrokerORM.id, isouter=True)

        # Проверка названия брокера
        if 'broker_name' in kwargs and kwargs['broker_name'] is not None:
            broker_alias = aliased(BrokerORM)
            query = query.join(broker_alias, cls.broker_id == broker_alias.id)
            conditions.append(broker_alias.name == kwargs['broker_name'])

        # Проверка названий валют
        if 'currency_names' in kwargs and kwargs['currency_names'] is not None:
            currency_conditions = []
            for currency_name in kwargs['currency_names']:
                upper_currency_name = currency_name.upper()
                currency_conditions.append(func.upper(cls.name).like(f"{upper_currency_name}%"))
                currency_conditions.append(func.upper(cls.name).like(f"%{upper_currency_name}"))
            conditions.append(or_(*currency_conditions))

        if conditions:
            query = query.where(*conditions)

        result = await db.scalars(query)
        return list(result.all())