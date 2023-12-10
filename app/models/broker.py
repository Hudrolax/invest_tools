from sqlalchemy import Column, Integer, String, select, asc
from sqlalchemy.exc import NoResultFound, IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship, aliased
from typing import Self, Sequence

from core.db import Base


class BrokerORM(Base):
    __tablename__ = "brokers"
    id = Column(Integer, primary_key=True, index=True) # type: ignore
    name = Column(String, unique=True, nullable=False) # type: ignore
    symbols = relationship('SymbolORM', back_populates='broker', cascade="all, delete")

    def __str__(self) -> str:
        return f'{self.name}'

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
    async def get_by_name(cls, db: AsyncSession, name: str) -> Self:
        result = (await db.scalars(select(cls).where(cls.name == name))).first()
        if not result:
            raise NoResultFound
        return result

    @classmethod
    async def get_filtered(cls, db: AsyncSession, **kwargs) -> Self:
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
    async def get_all(cls, db: AsyncSession) -> list[Self]:
        result = await db.execute(select(cls).order_by(asc(cls.id)))  # сортировка по возрастанию id
        return list(result.scalars().all())
