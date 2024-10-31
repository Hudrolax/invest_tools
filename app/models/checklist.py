from sqlalchemy import Column, Integer, String, select, asc, BOOLEAN, and_, DateTime, ForeignKey
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from .base_object import BaseDBObject


class ChecklistORM(BaseDBObject):
    __tablename__ = "checklist"  # type: ignore
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, nullable=False)
    checked = Column(BOOLEAN, nullable=False, default=False)
    date = Column(DateTime(timezone=True), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    user = relationship('UserORM', back_populates='checklist')

    def __str__(self) -> str:
        return f'{self.name}'

    @classmethod
    async def create(cls, db: AsyncSession, **kwargs) -> 'ChecklistORM':
        try:
            transaction = cls(**kwargs)
            transaction.date = datetime.now(timezone.utc)
            transaction.checked = False
            db.add(transaction)
            await db.flush()
            await db.refresh(transaction)
        except IntegrityError:
            await db.rollback()
            raise
        return transaction

    @classmethod
    async def get_list(cls, db: AsyncSession, **filters) -> list['ChecklistORM']:
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
    
    @classmethod
    async def get_items_after_date(cls, db: AsyncSession, date: datetime) -> list['ChecklistORM']:
        """
        Возвращает список элементов, у которых значение атрибута 'date' больше указанной даты.
        """
        query = select(cls).where(cls.date < date).order_by(asc(cls.id))

        result = await db.execute(query)
        return list(result.scalars().all())
