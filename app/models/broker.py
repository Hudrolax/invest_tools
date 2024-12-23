from sqlalchemy import Column, Integer, String, select, asc
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship

from .base_object import BaseDBObject


class BrokerORM(BaseDBObject):
    __tablename__ = "brokers"  # type: ignore
    id = Column(Integer, primary_key=True, index=True)  # type: ignore
    name = Column(String, unique=True, nullable=False, index=True)  # type: ignore
    symbols = relationship("SymbolORM", back_populates="broker", cascade="all, delete")

    def __str__(self) -> str:
        return f"{self.name}"

    @classmethod
    async def get_by_name(cls, db: AsyncSession, name: str) -> 'BrokerORM':
        result = (await db.scalars(select(cls).where(cls.name == name))).first()
        if not result:
            raise NoResultFound(f'broker with name {name} not found')
        return result

    @classmethod
    async def get_filtered(cls, db: AsyncSession, **kwargs) -> 'BrokerORM':
        conditions = []

        for key, value in kwargs.items():
            conditions.append(getattr(cls, key) == value)

        query = select(cls).where(*conditions)

        # Если нет условий фильтрации, вернет первую запись по умолчанию
        result = await db.scalars(query)
        symbol = result.first()

        if not symbol:
            raise NoResultFound("No matching symbol found")

        return symbol

    @classmethod
    async def get_all(cls, db: AsyncSession) -> list['BrokerORM']:
        result = await db.execute(
            select(cls).order_by(asc(cls.id))
        )  # сортировка по возрастанию id
        return list(result.scalars().all())
