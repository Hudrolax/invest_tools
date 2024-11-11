from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint, BOOLEAN
from sqlalchemy.orm import relationship

from .base_object import BaseDBObject


class ChartSettingsORM(BaseDBObject):
    __tablename__ = "chart_settings"  # type: ignore
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    symbol_id = Column(Integer, ForeignKey('symbols.id', ondelete='CASCADE'), nullable=False)
    timeframe = Column(Integer, nullable=True, default=240)
    show_order_icons = Column(BOOLEAN, nullable=True, default=True)
    __table_args__ = (
        UniqueConstraint('user_id', 'symbol_id', name='_chart_settings_user_id_symbol_id_uc'),
    )

    user = relationship('UserORM', back_populates='chart_settings')
    symbol = relationship('SymbolORM', back_populates='chart_settings')

    def __str__(self) -> str:
        return f'Chart settings user_id {self.user_id} symbol_id {self.symbol_id} timeframe {self.timeframe}'
