from sqlalchemy import Column, Integer, String, select, asc
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship

from brokers.binance import binance_symbols
from models.symbol import SymbolORM
from models.broker import BrokerORM

from .base_object import BaseDBObject

class CurrencyORM(BaseDBObject):
    __tablename__ = "currencies"  # type: ignore
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    wallets = relationship('WalletORM', back_populates='currency', cascade="all, delete")

    def __str__(self) -> str:
        return f'{self.name}'

    @classmethod
    async def create(cls, db: AsyncSession, **kwargs) -> 'CurrencyORM':
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
    async def get_all(cls, db: AsyncSession) -> list['CurrencyORM']:
        result = await db.execute(select(cls).order_by(asc(cls.id)))  # сортировка по возрастанию id
        return list(result.scalars().all())


    @classmethod
    async def get_by_name(cls, db: AsyncSession, name: str | Column[str]) -> 'CurrencyORM':
        result = (await db.scalars(select(cls).where(cls.name == name))).first()
        if not result:
            raise NoResultFound
        return result
