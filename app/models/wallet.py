from sqlalchemy import Column, Integer, String, select, asc, ForeignKey, DECIMAL, and_, BOOLEAN
from sqlalchemy.exc import NoResultFound, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship
from typing import Self

from .base_object import BaseDBObject
from models.user_wallets import UserWalletsORM


class WalletORM(BaseDBObject):
    __tablename__ = "wallets"  # type: ignore
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    currency_id = Column(Integer, ForeignKey('currencies.id', ondelete='CASCADE'), nullable=False)
    balance = Column(DECIMAL(precision=20, scale=8), nullable=False, default=0)
    color = Column(String, default="#f9a60a")
    in_balance = Column(BOOLEAN, default=True, nullable=False)

    currency = relationship('CurrencyORM', back_populates='wallets')
    wallet_transactions = relationship('WalletTransactionORM', back_populates='wallet', cascade="all, delete")
    wallet_users = relationship('UserWalletsORM', back_populates='wallet', cascade="all, delete")

    def __str__(self) -> str:
        return f'{self.name}'
    
    @classmethod
    async def create(cls, db: AsyncSession, **kwargs) -> Self:
        try:
            user_id = kwargs.pop('user_id')
            transaction = cls(**kwargs)
            db.add(transaction)

            # create user relationship

            await db.flush()
            await db.refresh(transaction)
            await UserWalletsORM.create(db, user_id=user_id, wallet_id=transaction.id)

        except IntegrityError:
            await db.rollback()
            raise
        return transaction

    @classmethod
    async def get_by_id_and_wallet_id(cls, db: AsyncSession, id: int) -> Self:
        result = (await db.scalars(select(cls).where(cls.id == id))).first()
        if not result:
            raise NoResultFound
        return result

    @classmethod
    async def get_all(cls, db: AsyncSession) -> list[Self]:
        result = await db.execute(select(cls).order_by(asc(cls.id)))  # сортировка по возрастанию id
        return list(result.scalars().all())

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
