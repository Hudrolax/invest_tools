from sqlalchemy import Column, Integer, select, asc, ForeignKey, and_, UniqueConstraint
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship
from typing import Self, Union

from .base_object import BaseDBObject


class UserWalletsORM(BaseDBObject):
    __tablename__ = "user_wallets"  # type: ignore
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
    async def get_by_id_and_wallet_id(cls, db: AsyncSession, raise_exeption: bool = True, **kwargs) -> Union[Self, None]:
        result = await db.execute(select(cls).filter_by(**kwargs))
        existing = result.scalars().first()
        
        if existing:
            return existing
        else:
            if raise_exeption:
                raise NoResultFound
            return None

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
