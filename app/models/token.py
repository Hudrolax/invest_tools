from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, select, asc
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship
from typing import Self, Sequence

from .base_object import BaseDBObject


class TokenORM(BaseDBObject):
    __tablename__ = "tokens"  # type: ignore
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=False)
    token = Column(String, nullable=False, index=True)
    description = Column(String, nullable=False)
    expiration_date = Column(DateTime, index=True)

    user = relationship('UserORM', back_populates='tokens')

    @classmethod
    async def get_by_token(cls, db: AsyncSession, token: str) -> Self | None:
        """Return token istance by it's value"""
        result = (await db.scalars(select(cls).where(cls.token == token))).first()
        if not result:
            raise NoResultFound
        return result

    @classmethod
    async def get_user_tokens(cls, db: AsyncSession, user_id: int) -> Sequence[Self]:
        """Returns user tokens"""
        result = await db.execute(select(cls).where(cls.user_id == user_id).order_by(asc(cls.id)))  # сортировка по возрастанию id
        return result.scalars().all()
