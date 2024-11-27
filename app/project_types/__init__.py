from pydantic import BaseModel, validator
from decimal import Decimal
from datetime import datetime

class Kline(BaseModel):
    start: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    @validator("open", "high", "low", "close", pre=True)
    def format_numeric_fields(cls, value):
        return Decimal(value)

    @validator("start", pre=True)
    def format_date_fields(cls, value):
        def handle_int_value(val: int) -> datetime:
            if val > 10**10:
                return datetime.fromtimestamp(val / 1000)
            else:
                return datetime.fromtimestamp(val)
        
        if isinstance(value, int):
            return handle_int_value(value)
        elif isinstance(value, datetime):
            return value
        elif isinstance(value, str):
            try:
                return handle_int_value(int(value))
            except:
                return datetime.fromisoformat(value)
        else:
            raise TypeError('start should be timestamp or datetime')
