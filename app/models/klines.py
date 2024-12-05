from sqlalchemy import (
    Column,
    Integer,
    TIMESTAMP,
    DECIMAL,
    String,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound, IntegrityError, OperationalError

from models.broker import BrokerORM
from models.symbol import SymbolORM
from .base_object import BaseDBObject
from brokers.bybit import BybitTimeframe, BybitBroker
from project_types import Kline
from datetime import datetime


class KlineORM(BaseDBObject):
    __tablename__ = "klines"  # type: ignore
    symbol_id = Column(Integer, nullable=False, index=True, primary_key=True)
    interval = Column(String, nullable=False, index=True, primary_key=True)
    start = Column(TIMESTAMP, nullable=False, index=True, primary_key=True)
    open = Column(DECIMAL, nullable=False, index=True)
    high = Column(DECIMAL, nullable=False, index=True)
    low = Column(DECIMAL, nullable=False, index=True)
    close = Column(DECIMAL, nullable=False, index=True)

    def __str__(self):
        return f"kline symbol_id {self.symbol_id} interval {self.interval} start {self.start} o {self.open} h {self.high} l {self.low} c {self.close}"

    @classmethod
    async def delete(cls, db: AsyncSession, symbol_id: int | Column[int], interval: str | Column[str], start: datetime | Column[datetime]) -> bool:  # type: ignore
        try:
            # попытаться получить существующую запись
            existing_entry = await db.get(cls, (symbol_id, interval, start))
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
    async def update(  # type: ignore
        cls,
        db: AsyncSession,
        symbol_id: int | Column[int],
        interval: str | Column[str],
        start: datetime | Column[datetime],
        **kwargs,
    ) -> "KlineORM":
        try:
            # попытаться получить существующую запись
            existing_entry = await db.get(cls, (symbol_id, interval, start))
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
    async def check_and_del_old_klines(cls, db: AsyncSession, symbol_id: int | Column[int], interval: BybitTimeframe):
        query = (
            select(KlineORM)
            .select_from(KlineORM)
            .where((KlineORM.interval == interval) & (KlineORM.symbol_id == symbol_id))
            .order_by(KlineORM.start)
        )
        klines = (await db.execute(query)).all()
        if klines:
            symbol = await SymbolORM.get_by_id(db, id=symbol_id)
            max_klines_count = symbol.klines_max_count if symbol.klines_max_count else 200
            if len(klines) > max_klines_count:
                klines_for_delete = klines[0 : -max_klines_count]
                for del_kline in klines_for_delete:
                    await KlineORM.delete(
                        db,
                        symbol_id=symbol_id,
                        interval=interval,
                        start=del_kline.start,
                    )

    @classmethod
    async def append_update(
        cls,
        db: AsyncSession,
        interval: BybitTimeframe,
        kline: Kline,
        symbol_id: int | Column[int] | None = None,
        symbol_name: str | None = None,
        broker_name: BybitBroker | None = None,
    ) -> "KlineORM":
        if symbol_id is None and symbol_name is None:
            raise ValueError("One of symbol_id or symbol_name should be passed!")
        if symbol_name and not broker_name:
            raise ValueError("If symbol_name passed broker_name should passed too!")

        query = (
            select(KlineORM)
            .select_from(KlineORM)
            .where((KlineORM.interval == interval) & (KlineORM.start == kline.start))
        )
        if symbol_id is not None:
            query = query.where(KlineORM.symbol_id == symbol_id)
        elif symbol_name is not None:
            query = query.join(
                SymbolORM,
                (SymbolORM.id == KlineORM.symbol_id) & (SymbolORM.name == symbol_name),
            ).join(
                BrokerORM,
                (BrokerORM.name == broker_name) & (BrokerORM.id == SymbolORM.broker_id),
            )

        kline_instance = (await db.execute(query)).scalar_one_or_none()

        if kline_instance is None:
            if symbol_id is not None:
                symbol = await SymbolORM.get_by_id(db, id=symbol_id)
            else:
                symbol = await SymbolORM.get_by_name_and_broker(db, name=symbol_name, broker_name=broker_name)

            kline_instance = await KlineORM.create(
                db,
                symbol_id=symbol.id,
                interval=interval,
                start=kline.start,
                open=kline.open,
                high=kline.high,
                low=kline.low,
                close=kline.close,
            )
            await cls.check_and_del_old_klines(db, symbol_id=symbol.id, interval=interval)
            return kline_instance
        else:
            return await KlineORM.update(
                db,
                symbol_id=kline_instance.symbol_id,
                interval=kline_instance.interval,
                start=kline_instance.start,
                open=kline.open,
                high=kline.high,
                low=kline.low,
                close=kline.close,
            )
