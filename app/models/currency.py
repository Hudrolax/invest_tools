from sqlalchemy import Column, Integer, String, select, asc
from sqlalchemy.exc import NoResultFound, IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship
from typing import Self

from core.db import Base
from brokers.binance import binance_symbols
from models.symbol import SymbolORM
from models.broker import BrokerORM


class CurrencyORM(Base):
    __tablename__ = "currencies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    wallets = relationship('WalletORM', back_populates='currency', cascade="all, delete")

    def __str__(self) -> str:
        return f'{self.name}'

    @classmethod
    async def create(cls, db: AsyncSession, **kwargs) -> Self:
        try:
            transaction = cls(**kwargs)
            db.add(transaction)

            # add symbols with this currency
            broker = await BrokerORM.get_by_name(db, 'Binance-spot')
            broker_id = broker.id
            actual_symbols = ['BTCUSDT', 'BTCRUB', 'BTCARS', 'USDTRUB', 'USDTARS']
            for symbol_name in actual_symbols:
                if symbol_name in binance_symbols['Binance-spot']:
                    symbols = await SymbolORM.get_list(db, symbol_names=[symbol_name], broker_name=broker.name)
                    if not symbols:
                        await SymbolORM.create(db, name=symbol_name, broker_id=broker_id)

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
    async def get_all(cls, db: AsyncSession) -> list[Self]:
        result = await db.execute(select(cls).order_by(asc(cls.id)))  # сортировка по возрастанию id
        return list(result.scalars().all())