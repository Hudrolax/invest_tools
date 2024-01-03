from sqlalchemy import (Column, Integer, String, select, asc, BigInteger,
    ForeignKey, DECIMAL, DateTime, TEXT, select, and_, true)
from sqlalchemy.exc import NoResultFound, IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship
from typing import Self
from datetime import datetime
import uuid
from decimal import Decimal

from core.db import Base
from models.wallet import WalletORM
from models.symbol import SymbolORM
from models.currency import CurrencyORM


async def get_symbol_rate(db: AsyncSession, symbol_name: str, broker_name:str) -> Decimal:
    symbols = await SymbolORM.get_list(db, symbol_names=[symbol_name], broker_name=broker_name)
    rate = symbols[0].rate
    return rate if isinstance(rate, Decimal) else Decimal(1)


class WalletTransactionORM(Base):
    __tablename__ = "wallet_transactions"
    id = Column(BigInteger, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey('wallets.id', ondelete='CASCADE'), nullable=False, index=True)
    exin_item_id = Column(Integer, ForeignKey('exin_items.id', ondelete='CASCADE'), index=True)
    amount = Column(DECIMAL(precision=20, scale=8), nullable=False)
    amountBTC = Column(DECIMAL(precision=20, scale=8), nullable=False)
    amountUSD = Column(DECIMAL(precision=20, scale=2), nullable=False)
    amountRUB = Column(DECIMAL(precision=20, scale=2), nullable=False)
    amountARS = Column(DECIMAL(precision=20, scale=2), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    date = Column(DateTime(timezone=True), nullable=False) 
    doc_id = Column(String, nullable=False, index=True)
    comment = Column(TEXT)

    wallet = relationship('WalletORM', back_populates='wallet_transactions')
    exin_item = relationship('ExInItemORM', back_populates='wallet_transactions')
    user = relationship('UserORM', back_populates='wallet_transactions')

    def __str__(self) -> str:
        return f'{self.date} {self.wallet} {self.exin_item} {self.amount}'

    async def delete_self(self, db: AsyncSession):
        await self.delete(db, self.id) # type: ignore

    @classmethod
    async def create(cls, db: AsyncSession, **kwargs) -> Self:
        try:
            transaction = cls(**kwargs)
            if not kwargs.get('date'):
                transaction.date = datetime.now()
            if not kwargs.get('doc_id'):
                transaction.doc_id = str(uuid.uuid4())
            

            # change wallet balance
            wallet = await WalletORM.get(db, transaction.wallet_id) # type: ignore
            wallet.balance += Decimal(transaction.amount) # type: ignore
            wallet_currency = await CurrencyORM.get(db, wallet.currency_id) # type: ignore
            wc_name = wallet_currency.name

            if wc_name == 'BTC': # type: ignore
                BTCUSDT_rate = await get_symbol_rate(db, 'BTCUSDT', 'Binance-spot')
                BTCRUB_rate = await get_symbol_rate(db, 'BTCRUB', 'Binance-spot')
                BTCARS_rate = await get_symbol_rate(db, 'BTCARS', 'Binance-spot')
                transaction.amountBTC = Decimal(transaction.amount) # type: ignore
                transaction.amountUSD = Decimal(transaction.amount) * BTCUSDT_rate # type: ignore
                transaction.amountRUB = Decimal(transaction.amount) * BTCRUB_rate # type: ignore
                transaction.amountARS = Decimal(transaction.amount) * BTCARS_rate # type: ignore
            elif wc_name == 'USD': # type: ignore
                BTCUSDT_rate = await get_symbol_rate(db, 'BTCUSDT', 'Binance-spot')
                USDTRUB_rate = await get_symbol_rate(db, 'USDTRUB', 'Binance-spot')
                USDTARS_rate = await get_symbol_rate(db, 'USDTARS', 'Binance-spot')
                transaction.amountBTC = Decimal(transaction.amount) / BTCUSDT_rate # type: ignore
                transaction.amountUSD = Decimal(transaction.amount) # type: ignore
                transaction.amountRUB = Decimal(transaction.amount) * USDTRUB_rate # type: ignore
                transaction.amountARS = Decimal(transaction.amount) * USDTARS_rate # type: ignore
            elif wc_name == 'ARS': # type: ignore
                USDTRUB_rate = await get_symbol_rate(db, 'USDTRUB', 'Binance-spot')
                USDTARS_rate = await get_symbol_rate(db, 'USDTARS', 'Binance-spot')
                BTCARS_rate = await get_symbol_rate(db, 'BTCARS', 'Binance-spot')
                transaction.amountBTC = Decimal(transaction.amount) / BTCARS_rate # type: ignore
                transaction.amountUSD = Decimal(transaction.amount) / USDTARS_rate # type: ignore
                transaction.amountRUB = Decimal(transaction.amount) / USDTARS_rate * USDTRUB_rate # type: ignore
                transaction.amountARS = Decimal(transaction.amount) # type: ignore
            elif wc_name == 'RUB': # type: ignore
                USDTRUB_rate = await get_symbol_rate(db, 'USDTRUB', 'Binance-spot')
                USDTARS_rate = await get_symbol_rate(db, 'USDTARS', 'Binance-spot')
                BTCRUB_rate = await get_symbol_rate(db, 'BTCRUB', 'Binance-spot')
                transaction.amountBTC = Decimal(transaction.amount) / BTCRUB_rate # type: ignore
                transaction.amountUSD = Decimal(transaction.amount) / USDTRUB_rate # type: ignore
                transaction.amountRUB = Decimal(transaction.amount) # type: ignore
                transaction.amountARS = Decimal(transaction.amount) / USDTRUB_rate * USDTARS_rate # type: ignore

            db.add(transaction)
            await db.flush()
            await db.refresh(transaction)
        except IntegrityError:
            await db.rollback()
            raise
        return transaction

    # @classmethod
    # async def update(cls, db: AsyncSession, id: int, **kwargs) -> Self:
    #     try:
    #         # попытаться получить существующую запись
    #         existing_entry = await db.get(cls, id)
    #         if not existing_entry:
    #             raise NoResultFound
            
    #         # обновление полей записи
    #         for attr, value in kwargs.items():
    #             setattr(existing_entry, attr, value)

    #         await db.flush()
    #     except IntegrityError:
    #         await db.rollback()
    #         raise
    #     return existing_entry
    
    @classmethod
    async def delete(cls, db: AsyncSession, id: int) -> bool:
        try:
            # попытаться получить существующую запись
            existing_entry = await db.get(cls, id)
            if not existing_entry:
                raise NoResultFound

            wallet = await WalletORM.get(db, existing_entry.wallet_id) # type: ignore
            wallet.balance -= Decimal(existing_entry.amount) # type: ignore

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
    async def get_list(cls, db: AsyncSession, **filters) -> list[Self]:
        """Returns filtered list of instances"""
        query = select(cls).order_by(asc(cls.id))

        filter_clauses = [getattr(cls, key) == value for key, value in filters.items() if value is not None]
        
        if filter_clauses:
            query = query.filter(and_(*filter_clauses))
        else:
            # Используется true() для создания условия, которое всегда истинно
            query = query.filter(true())

        result = await db.execute(query)
        return list(result.scalars().all())