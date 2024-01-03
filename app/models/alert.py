from sqlalchemy import (Column, Integer, DateTime, DECIMAL, select,
    asc, ForeignKey, String, BOOLEAN, TEXT)
from sqlalchemy.exc import NoResultFound, IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship, joinedload
from typing import Self, Literal
from datetime import datetime
from decimal import Decimal

from core.db import Base

from models.user import UserORM
from models.symbol import SymbolORM
from models.broker import BrokerORM


Triggers = Literal['above', 'below']


class AlertORM(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    symbol_id = Column(Integer, ForeignKey('symbols.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    price = Column(DECIMAL(precision=20, scale=8), nullable=False)
    trigger = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True) 
    triggered_at = Column(DateTime(timezone=True), nullable=True, default=None, index=True) 
    is_active = Column(BOOLEAN, nullable=False, default=True)
    is_sent = Column(BOOLEAN, nullable=False, default=False)
    comment = Column(TEXT)

    symbol = relationship('SymbolORM', back_populates='alerts')
    user = relationship('UserORM', back_populates='alerts')

    def __str__(self):
        return f'alert {self.symbol} {self.trigger} {self.price}'

    @classmethod
    async def validate(cls, alert: 'AlertORM.instance', db: AsyncSession) -> None:
        if not alert.price or alert.price < 0:
            raise ValueError('Price should be greater than zero.')
        
        user = (await db.scalars(select(UserORM).where(UserORM.id == alert.user_id))).first()
        symbol = (await db.scalars(select(SymbolORM).where(SymbolORM.id == alert.symbol_id))).first()

        if not user:
            raise ValueError(f'User with id {alert.user_id} not found.')
        if not symbol:
            raise ValueError(f'Symbol with id {alert.symbol_id} not found.')
        
        if alert.trigger not in ['above', 'below']:
            raise ValueError(f'trigger should be in list {['above', 'below']}')
        
        if alert.is_active and alert.is_sent:
            raise ValueError("Alert can't be active and is_sent at the same time.")

    @classmethod
    async def create(cls, db: AsyncSession, **kwargs) -> Self:
        try:
            try:
                symbol_name = kwargs.pop('symbol_name')
            except KeyError:
                raise ValueError('symbol_name not passed')
            try:
                broker_name = kwargs.pop('broker_name')
            except KeyError:
                raise ValueError('broker_name not passed')

            try:
                broker = await BrokerORM.get_by_name(db, broker_name)
            except NoResultFound:
                raise ValueError(f'Broker with name {broker_name} not found')

            symbol = await SymbolORM.get_or_create(db, symbol_name, broker_id=broker.id) # type: ignore
            kwargs['symbol_id'] = symbol.id

            alert = cls(**kwargs)
            alert.created_at = datetime.now()

            if isinstance(alert.price, int) or isinstance(alert.price, str):
                alert.price = Decimal(alert.price)


            db.add(alert)
            await db.flush()
            await cls.validate(alert, db)
        except (IntegrityError, ValueError):
            await db.rollback()
            raise
        return alert

    @classmethod
    async def update(cls, db: AsyncSession, id: int, **kwargs) -> Self:
        try:
            # попытаться получить существующую запись
            existing_entry = await db.get(cls, id)
            if not existing_entry:
                raise NoResultFound
            
            if kwargs.get('price'):
                if isinstance(kwargs['price'], int) or isinstance(kwargs['price'], str) \
                    or isinstance(kwargs['price'], float):
                    kwargs['price'] = Decimal(kwargs['price'])
            
            if kwargs.get('symbol_name'):
                symbol_name = kwargs.pop('symbol_name')
                try:
                    symbol = await SymbolORM.get_by_name(db, symbol_name)
                    kwargs['symbol_id'] = symbol.id
                except NoResultFound:
                    raise ValueError(f'Symbol with name {symbol_name} not found')

            # обновление полей записи
            for attr, value in kwargs.items():
                setattr(existing_entry, attr, value)

            await db.flush()
            await cls.validate(existing_entry, db)
        except (IntegrityError, ValueError):
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
        result = (await db.scalars(select(cls).options(joinedload(AlertORM.symbol)).where(cls.id == id))).first()
        if not result:
            raise NoResultFound
        return result


    @classmethod
    async def get_filtered_alerts(
        cls,
        db: AsyncSession,
        user: UserORM | None = None,
        broker_name: str | None = None,
        symbol_name: str | None = None,
        is_active: bool | None = None,
        is_sent: bool | None = None,
        is_triggered: bool | None = None
    ) -> list['AlertORM']:
        query = select(AlertORM).options(joinedload(AlertORM.symbol))
        if user is not None:
            query = query.filter(AlertORM.user_id == user.id)
        if broker_name is not None:
            query = query.join(AlertORM.symbol).join(SymbolORM.broker).filter(BrokerORM.name == broker_name)
        # if symbol_name is not None:
        #     query = query.join(AlertORM.symbol).filter(SymbolORM.name == symbol_name)
        if symbol_name is not None:
            pattern = f"%{symbol_name}%"
            query = query.join(AlertORM.symbol).filter(SymbolORM.name.like(pattern))
        if is_active is not None:
            query = query.filter(AlertORM.is_active == is_active)
        if is_sent is not None:
            query = query.filter(AlertORM.is_sent == is_sent)
        if is_triggered is not None:
            # Проверяем наличие или отсутствие поля triggered_at
            condition = AlertORM.triggered_at != None if is_triggered else AlertORM.triggered_at == None
            query = query.filter(condition)

        result = await db.execute(query)
        return list(result.scalars().all()) 

    @classmethod
    async def get_filtered_alerts_unauthorized(
        cls,
        db: AsyncSession,
        broker_name: str | None = None,
        symbol_name: str | None = None,
        is_active: bool | None = None,
        is_sent: bool | None = None,
        is_triggered: bool | None = None
    ) -> list['AlertORM']:
        query = select(AlertORM).options(joinedload(AlertORM.symbol))
        if broker_name is not None:
            query = query.join(AlertORM.symbol).join(SymbolORM.broker).filter(BrokerORM.name == broker_name)
        if symbol_name is not None:
            query = query.join(AlertORM.symbol).filter(SymbolORM.name == symbol_name)
        if is_active is not None:
            query = query.filter(AlertORM.is_active == is_active)
        if is_sent is not None:
            query = query.filter(AlertORM.is_sent == is_sent)
        if is_triggered is not None:
            # Проверяем наличие или отсутствие поля triggered_at
            condition = AlertORM.triggered_at != None if is_triggered else AlertORM.triggered_at == None
            query = query.filter(condition)

        result = await db.execute(query)
        return list(result.scalars().all()) 