from sqlalchemy import (
    Column,
    select,
)
from sqlalchemy.exc import NoResultFound, IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import declared_attr
from typing import Any

from core.db import Base


class BaseDBObject(Base):
    __abstract__ = True

    @classmethod  # type: ignore
    @declared_attr  # type: ignore
    def __tablename__(cls) -> str:
        return "replace_this_tablename"

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in self.__dict__.items() if not key.startswith('_')}

    @classmethod
    async def validate(cls, *args, **kwargs) -> None:
        pass

    @classmethod
    async def create(cls, db: AsyncSession, **kwargs) -> 'BaseDBObject':
        try:
            transaction = cls(**kwargs)
            db.add(transaction)
            await db.flush()
        except IntegrityError:
            await db.rollback()
            raise
        return transaction

    @classmethod
    async def update(cls, db: AsyncSession, id: int | Column[int], **kwargs) -> 'BaseDBObject':
        try:
            # попытаться получить существующую запись
            existing_entry = await db.get(cls, id)
            if not existing_entry:
                raise NoResultFound

            # обновление полей записи
            for attr, value in kwargs.items():
                setattr(existing_entry, attr, value)

            await db.flush()
            await cls.validate(existing_entry, db)
        except IntegrityError:
            await db.rollback()
            raise
        return existing_entry

    @classmethod
    async def delete(cls, db: AsyncSession, id: int | Column[int]) -> bool:
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
    async def get_by_id(cls, db: AsyncSession, id: int | Column[int]) -> 'BaseDBObject':
        result = (await db.scalars(select(cls).where(cls.id == id))).first()
        if not result:
            raise NoResultFound
        return result

    @classmethod
    async def get(cls, db: AsyncSession, id: int | Column[int]) -> 'BaseDBObject':
        return await cls.get_by_id(db, id)
