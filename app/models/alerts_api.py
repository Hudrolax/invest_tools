from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime
from typing import Optional, Literal


class NewAlertWithoutId(BaseModel):
    """A new alert instance"""
    symbol_id: int
    user_id: int
    price: Decimal
    trigger: Literal['above', 'below']


class Alert(NewAlertWithoutId):
    """An alert instance with ID"""
    id: int
    created_at: datetime
    triggered_at: datetime | None = None
    triggered: bool = False
    is_active: bool = True
    is_sent: bool = False


class AlertUpdate(BaseModel):
    """An alert instance with ID"""
    symbol_id: Optional[str] = None
    price: Optional[Decimal] = None
    trigger: Optional[Literal['above', 'below']] = None
    created_at: Optional[datetime] = None
    triggered_at: Optional[datetime | None] = None
    triggered: Optional[bool] = None
    is_active: Optional[bool] = None
    is_sent: Optional[bool] = None


class Alerts(BaseModel):
    """List of alerts"""
    alerts: list[Alert]