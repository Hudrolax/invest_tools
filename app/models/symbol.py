from sqlalchemy import Column, Integer, String, select, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, aliased, joinedload
from sqlalchemy.exc import NoResultFound, IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Self, Sequence

from core.db import Base
from models.broker import BrokerORM


class SymbolORM(Base):
    __tablename__ = "symbols"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    broker_id = Column(Integer, ForeignKey('brokers.id', ondelete='CASCADE'), nullable=False)
    __table_args__ = (
        UniqueConstraint('name', 'broker_id', name='_symbol_name_broker_id_uc'),
    )

    broker = relationship('BrokerORM', back_populates='symbols')
    alerts = relationship('AlertORM', back_populates='symbol', cascade="all, delete")

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
    async def get_or_create(cls, db: AsyncSession, name: str, broker_id: int) -> Self:
        result = (await db.scalars(select(cls).where(cls.name == name, cls.broker_id==broker_id))).first()
        if not result:
            result = await cls.create(db, name=name, broker_id=broker_id)
        return result

    @classmethod
    async def get_all(cls, db: AsyncSession) -> Sequence[Self]:
        result = await db.execute(
            select(cls).options(joinedload(cls.broker)).order_by(cls.id.asc())
        )
        return result.scalars().all()

    @classmethod
    async def get_filtered(cls, db: AsyncSession, **kwargs) -> 'SymbolORM':
        conditions = []

        for key, value in kwargs.items():
            # Отделяем случай фильтрации по `broker_name`
            if key == 'broker_name':
                # Создаем псевдоним для таблицы `BrokerORM` при необходимости соединения
                broker_alias = aliased(BrokerORM)
                conditions.append(broker_alias.name == value)
            else:
                # Для других полей используем атрибуты класса напрямую
                conditions.append(getattr(cls, key) == value)

        query = select(cls).join(BrokerORM, isouter=True).where(*conditions)

        # Если нет условий фильтрации, вернет первую запись по умолчанию
        result = await db.scalars(query)
        symbol = result.first()

        if not symbol:
            raise NoResultFound("No matching symbol found")

        return symbol
