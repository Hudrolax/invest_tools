from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    UniqueConstraint,
    BOOLEAN,
    DECIMAL,
    select,
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from .base_object import BaseDBObject


class ChartSettingsORM(BaseDBObject):
    __tablename__ = "chart_settings"  # type: ignore
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    symbol_id = Column(
        Integer, ForeignKey("symbols.id", ondelete="CASCADE"), nullable=False
    )
    timeframe = Column(Integer, nullable=True, default=240)
    show_order_icons = Column(BOOLEAN, nullable=True, default=True)
    taker_fee_rate = Column(DECIMAL, nullable=True)
    maker_fee_rate = Column(DECIMAL, nullable=True)
    __table_args__ = (
        UniqueConstraint(
            "user_id", "symbol_id", name="_chart_settings_user_id_symbol_id_uc"
        ),
    )

    user = relationship("UserORM", back_populates="chart_settings")
    symbol = relationship("SymbolORM", back_populates="chart_settings")

    def __str__(self) -> str:
        return f"Chart settings user_id {self.user_id} symbol_id {self.symbol_id} timeframe {self.timeframe}"

    @classmethod
    async def get_or_create(
        cls,
        db: AsyncSession,
        user_id: int | Column[int],
        symbol_id: int | Column[int],
        timeframe: int | None = None,
        show_order_icons: bool | None = None,
        taker_fee_rate: Decimal | None = None,
        maker_fee_rate: Decimal | None = None,
    ) -> "ChartSettingsORM":
        result = (
            await db.scalars(
                select(cls).where(cls.user_id == user_id, cls.symbol_id == symbol_id)
            )
        ).first()
        if not result:
            result = await cls.create(
                db,
                user_id=user_id,
                symbol_id=symbol_id,
                timeframe=timeframe,
                show_order_icons=show_order_icons,
                taker_fee_rate=taker_fee_rate,
                maker_fee_rate=maker_fee_rate,
            )
        return result
