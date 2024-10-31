from sqlalchemy import Column, Integer, select, asc, ForeignKey, and_, UniqueConstraint
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship

from .base_object import BaseDBObject


class UserExInItemORM(BaseDBObject):
    __tablename__ = "user_exin_items"  # type: ignore
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    exin_item_id = Column(Integer, ForeignKey('exin_items.id', ondelete='CASCADE'), nullable=False)
    __table_args__ = (
        UniqueConstraint('user_id', 'exin_item_id', name='_user_exin_items_user_id_exin_item_id_uc'),
    )

    user = relationship('UserORM', back_populates='user_exin_items')
    exin_item = relationship('ExInItemORM', back_populates='users')

    def __str__(self) -> str:
        return f'user_id {self.user_id} wallet_id {self.wallet_id}'

    @classmethod
    async def get_list(cls, db: AsyncSession, **filters) -> list['UserExInItemORM']:
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
