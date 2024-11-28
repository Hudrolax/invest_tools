from sqlalchemy import (
    BOOLEAN,
    Column,
    Integer,
    TIMESTAMP,
    DECIMAL,
    select,
    ForeignKey,
    String,
)
from sqlalchemy.exc import NoResultFound, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship

from models.symbol import SymbolORM
from models.broker import BrokerORM
from typing import Literal
from datetime import datetime
from decimal import Decimal
from .base_object import BaseDBObject


LineType = Literal["trendLine", "horizontalLine", "horizontalRay"]
LINE_TYPES = ["trendLine", "horizontalLine", "horizontalRay"]


class LineORM(BaseDBObject):
    __tablename__ = "lines"  # type: ignore
    id = Column(Integer, primary_key=True, index=True)
    symbol_id = Column(
        Integer,
        ForeignKey("symbols.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line_type = Column(String, nullable=False)
    x0 = Column(TIMESTAMP, nullable=False, index=True)
    y0 = Column(DECIMAL(precision=20, scale=8), nullable=False, index=True)
    x1 = Column(TIMESTAMP, nullable=True, index=True)
    y1 = Column(DECIMAL(precision=20, scale=8), nullable=True, index=True)
    label = Column(String, nullable=True)
    color = Column(String, nullable=False, default="#ffffff")
    width = Column(Integer, nullable=False, default=1)
    created_at = Column(TIMESTAMP, nullable=False, index=True)
    locked = Column(BOOLEAN, nullable=True, default=False)
    style = Column(String, nullable=True, default='solid')

    symbol = relationship("SymbolORM", back_populates="lines")
    user = relationship("UserORM", back_populates="lines")
    alerts = relationship("AlertORM", back_populates="line")

    def __str__(self):
        return f"line {self.symbol} p1 {self.x0}:{self.y0} p2 {self.x1}:{self.y1}"

    @classmethod
    async def create(cls, db: AsyncSession, **kwargs):
        try:
            try:
                symbol_name = kwargs.pop("symbol_name")
            except KeyError:
                raise ValueError("symbol_name not passed")
            try:
                broker_name = kwargs.pop("broker_name")
            except KeyError:
                raise ValueError("broker_name not passed")

            try:
                broker = await BrokerORM.get_by_name(db, broker_name)
            except NoResultFound:
                raise ValueError(f"Broker with name {broker_name} not found")

            symbol = await SymbolORM.get_or_create(db, symbol_name, broker_id=broker.id)  # type: ignore
            kwargs["symbol_id"] = symbol.id

            line = cls(**kwargs)
            line.created_at = datetime.now()

            if isinstance(line.y0, int) or isinstance(line.y0, str) or isinstance(line.y0, float):
                line.y0 = Decimal(line.y0)

            if isinstance(line.y1, int) or isinstance(line.y1, str) or isinstance(line.y1, float):
                line.y0 = Decimal(line.y1)

            db.add(line)
            await db.flush()
        except (IntegrityError, ValueError):
            await db.rollback()
            raise
        return line

    @classmethod
    async def update(cls, db: AsyncSession, id: int | Column[int], **kwargs):
        try:
            # попытаться получить существующую запись
            existing_entry = await db.get(cls, id)
            if not existing_entry:
                raise NoResultFound

            if kwargs.get("x0"):
                if isinstance(kwargs["x0"], int):
                    kwargs["x0"] = datetime.fromtimestamp(kwargs["x0"])

            if kwargs.get("x1"):
                if isinstance(kwargs["x1"], int):
                    kwargs["x1"] = datetime.fromtimestamp(kwargs["x1"])

            if kwargs.get("y0"):
                if isinstance(kwargs["y0"], int) or isinstance(kwargs["y0"], str) or isinstance(kwargs["y0"], float):
                    kwargs["y0"] = Decimal(kwargs["y0"])

            if kwargs.get("y1"):
                if isinstance(kwargs["y1"], int) or isinstance(kwargs["y1"], str) or isinstance(kwargs["y0"], float):
                    kwargs["y1"] = Decimal(kwargs["y1"])

            # обновление полей записи
            for attr, value in kwargs.items():
                setattr(existing_entry, attr, value)

            await db.flush()
        except IntegrityError:
            await db.rollback()
            raise
        return existing_entry

    @classmethod
    async def get_list(
        cls,
        db: AsyncSession,
        user_id: int,
        symbol_name: str,
    ) -> list["LineORM"]:

        query = select(cls).join(SymbolORM, SymbolORM.name == symbol_name).where(cls.usr_id == user_id)

        result = await db.scalars(query)
        return list(result.all())
