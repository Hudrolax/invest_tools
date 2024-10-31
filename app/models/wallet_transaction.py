from sqlalchemy import (Column, Integer, String, select, asc, BigInteger,
    ForeignKey, DECIMAL, DateTime, TEXT, and_)
from sqlalchemy.exc import NoResultFound, IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship
from typing import Self
from datetime import datetime
import uuid
from decimal import Decimal

from .base_object import BaseDBObject
from models.wallet import WalletORM
from models.symbol import SymbolORM
from models.currency import CurrencyORM


async def get_symbol_rate(db: AsyncSession, symbol_name: str, broker_name:str) -> Decimal:
    try:
        symbol = await SymbolORM.get_by_name_and_broker(db, symbol_name, broker_name=broker_name)
        rate = symbol.rate
        return rate  # type: ignore
    except NoResultFound:
        return Decimal(1)


class WalletTransactionORM(BaseDBObject):
    __tablename__ = "wallet_transactions"  # type: ignore
    id = Column(BigInteger, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey('wallets.id', ondelete='CASCADE'), nullable=False, index=True)
    exin_item_id = Column(Integer, ForeignKey('exin_items.id', ondelete='CASCADE'), index=True)
    amount = Column(DECIMAL(precision=20, scale=8), nullable=False)
    amountBTC = Column(DECIMAL(precision=20, scale=8), default=0)
    amountETH = Column(DECIMAL(precision=20, scale=8), default=0)
    amountUSD = Column(DECIMAL(precision=20, scale=2), default=0)
    amountRUB = Column(DECIMAL(precision=20, scale=2), default=0)
    amountARS = Column(DECIMAL(precision=20, scale=2), default=0)
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
            wallet_currency = await CurrencyORM.get(db, id=wallet.currency_id) # type: ignore
            if wallet_currency is None:
                raise Exception("Wallet currency is None!")
            wc_name = wallet_currency.name

            if wc_name == 'BTC': # type: ignore
                BTCUSDT_rate = await get_symbol_rate(db, 'BTCUSDT', 'Binance-spot')
                USDRUB_rate = await get_symbol_rate(db, 'USDRUB', 'investing.com')
                BTCARS_rate = await get_symbol_rate(db, 'BTCARS', 'Binance-spot')
                ETHBTC_rate = await get_symbol_rate(db, 'ETHBTC', 'Binance-spot')
                transaction.amountBTC = Decimal(transaction.amount) # type: ignore
                transaction.amountUSD = Decimal(transaction.amount) * BTCUSDT_rate # type: ignore
                transaction.amountRUB = Decimal(transaction.amount) * BTCUSDT_rate  * USDRUB_rate # type: ignore
                transaction.amountARS = Decimal(transaction.amount) * BTCARS_rate # type: ignore
                transaction.amountETH = Decimal(transaction.amount) / ETHBTC_rate # type: ignore
            if wc_name == 'ETH': # type: ignore
                BTCUSDT_rate = await get_symbol_rate(db, 'BTCUSDT', 'Binance-spot')
                USDRUB_rate = await get_symbol_rate(db, 'USDRUB', 'investing.com')
                BTCARS_rate = await get_symbol_rate(db, 'BTCARS', 'Binance-spot')
                ETHBTC_rate = await get_symbol_rate(db, 'ETHBTC', 'Binance-spot')
                ETHUSDT_rate = await get_symbol_rate(db, 'ETHUSDT', 'Binance-spot')
                transaction.amountBTC = Decimal(transaction.amount) * ETHBTC_rate # type: ignore
                transaction.amountUSD = Decimal(transaction.amount) * ETHUSDT_rate # type: ignore
                transaction.amountRUB = Decimal(transaction.amount) * ETHUSDT_rate * USDRUB_rate # type: ignore
                transaction.amountARS = Decimal(transaction.amount) * ETHBTC_rate * BTCARS_rate # type: ignore
                transaction.amountETH = Decimal(transaction.amount) # type: ignore
            elif wc_name == 'USD': # type: ignore
                BTCUSDT_rate = await get_symbol_rate(db, 'BTCUSDT', 'Binance-spot')
                USDRUB_rate = await get_symbol_rate(db, 'USDRUB', 'investing.com')
                USDTARS_rate = await get_symbol_rate(db, 'USDTARS', 'Binance-spot')
                ETHUSDT_rate = await get_symbol_rate(db, 'ETHUSDT', 'Binance-spot')
                transaction.amountBTC = Decimal(transaction.amount) / BTCUSDT_rate # type: ignore
                transaction.amountUSD = Decimal(transaction.amount) # type: ignore
                transaction.amountRUB = Decimal(transaction.amount) * USDRUB_rate # type: ignore
                transaction.amountARS = Decimal(transaction.amount) * USDTARS_rate # type: ignore
                transaction.amountETH = Decimal(transaction.amount) / ETHUSDT_rate # type: ignore
            elif wc_name == 'ARS': # type: ignore
                USDRUB_rate = await get_symbol_rate(db, 'USDRUB', 'investing.com')
                USDTARS_rate = await get_symbol_rate(db, 'USDTARS', 'Binance-spot')
                BTCARS_rate = await get_symbol_rate(db, 'BTCARS', 'Binance-spot')
                ETHBTC_rate = await get_symbol_rate(db, 'ETHBTC', 'Binance-spot')
                transaction.amountBTC = Decimal(transaction.amount) / BTCARS_rate # type: ignore
                transaction.amountUSD = Decimal(transaction.amount) / USDTARS_rate # type: ignore
                transaction.amountRUB = Decimal(transaction.amount) / USDTARS_rate * USDRUB_rate # type: ignore
                transaction.amountARS = Decimal(transaction.amount) # type: ignore
                transaction.amountETH = Decimal(transaction.amount) / BTCARS_rate / ETHBTC_rate # type: ignore
            elif wc_name == 'RUB': # type: ignore
                USDRUB_rate = await get_symbol_rate(db, 'USDRUB', 'investing.com')
                USDTARS_rate = await get_symbol_rate(db, 'USDTARS', 'Binance-spot')
                ETHBTC_rate = await get_symbol_rate(db, 'ETHBTC', 'Binance-spot')
                transaction.amountBTC = Decimal(transaction.amount) / USDRUB_rate / BTCUSDT_rate # type: ignore
                transaction.amountUSD = Decimal(transaction.amount) / USDRUB_rate # type: ignore
                transaction.amountRUB = Decimal(transaction.amount) # type: ignore
                transaction.amountARS = Decimal(transaction.amount) / USDRUB_rate * USDTARS_rate # type: ignore
                transaction.amountETH = Decimal(transaction.amount) / USDRUB_rate / ETHUSDT_rate # type: ignore

            db.add(transaction)
            await db.flush()
            await db.refresh(transaction)
        except IntegrityError:
            await db.rollback()
            raise
        return transaction

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
    async def get_list(cls, db: AsyncSession, **filters) -> list[Self]:
        """Returns filtered list of instances."""
        query = select(cls).order_by(asc(cls.id))

        if filters:
            filter_clauses = []
            for key, value in filters.items():
                if value is not None:
                    if isinstance(value, list):
                        # Если значение - список, используем оператор in_
                        filter_clauses.append(getattr(cls, key).in_(value))
                    else:
                        # Для обычных значений используем равенство
                        filter_clauses.append(getattr(cls, key) == value)

            query = query.filter(and_(*filter_clauses))

        result = await db.execute(query)
        return list(result.scalars().all())
