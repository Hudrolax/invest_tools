from sqlalchemy import Column, Integer, select, asc, ForeignKey, and_, UniqueConstraint
from sqlalchemy.exc import NoResultFound, IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship
from typing import Self

from core.db import Base


class UserWalletsORM(Base):
    __tablename__ = "user_wallets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    wallet_id = Column(Integer, ForeignKey('wallets.id', ondelete='CASCADE'), nullable=False)
    __table_args__ = (
        UniqueConstraint('user_id', 'wallet_id', name='_user_wallets_user_id_wallet_id_uc'),
    )

    user = relationship('UserORM', back_populates='user_wallets')
    wallet = relationship('WalletORM', back_populates='wallet_users')

    def __str__(self) -> str:
        return f'user_id {self.user_id} wallet_id {self.wallet_id}'

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
