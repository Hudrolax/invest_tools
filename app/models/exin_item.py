from sqlalchemy import Column, Integer, String, select, asc, BOOLEAN, UniqueConstraint, and_
from sqlalchemy.exc import  IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship
from typing import Self

from models.user_exin_items import UserExInItemORM
from .base_object import BaseDBObject


class ExInItemORM(BaseDBObject):
    __tablename__ = "exin_items"  # type: ignore
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    income = Column(BOOLEAN, nullable=False, default=False) # расходы или доходы
    __table_args__ = (
        UniqueConstraint('name', 'income', name='_exin_item_name_income_uc'),
    )

    wallet_transactions = relationship('WalletTransactionORM', back_populates='exin_item', cascade="all, delete")
    users = relationship('UserExInItemORM', back_populates='exin_item', cascade="all, delete")

    def __str__(self) -> str:
        return f'{self.name}'

    @classmethod
    async def create(cls, db: AsyncSession, **kwargs) -> Self:
        try:
            user_id = kwargs.pop('user_id')

            transaction = cls(**kwargs)
            db.add(transaction)
            await db.flush()

            await db.refresh(transaction)
            await UserExInItemORM.create(db, user_id=user_id, exin_item_id=transaction.id)
        except IntegrityError:
            await db.rollback()
            raise
        return transaction

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
