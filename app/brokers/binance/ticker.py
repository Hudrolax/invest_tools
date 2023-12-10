from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal
from typing import Annotated


class Ticker24hr(BaseModel):
    event_time: datetime
    symbol: str
    price_change: Decimal
    price_change_percent: Decimal
    last_price: Decimal
    last_quantity: Decimal
    open_price: Annotated[Decimal, 'Open price last 24 hr']
    high_price: Annotated[Decimal, 'High price last 24 hr']
    low_price: Annotated[Decimal, 'Low price last 24 hr']
    total_ba_volume: Annotated[Decimal, 'Total traded base asset volume']
    total_qa_volume: Annotated[Decimal, 'Total traded quote asset volume']
    total_trades: int

    @classmethod
    def from_dict(cls, data: dict):
        # Преобразование времени события / Event time из миллисекунд в datetime
        event_time = datetime.utcfromtimestamp(data["E"] / 1000)
        return cls(
            event_time=event_time,
            symbol=data["s"],
            price_change=Decimal(data["p"]),
            price_change_percent=Decimal(data["P"]),
            last_price=Decimal(data["c"]),
            last_quantity=Decimal(data["Q"]),
            open_price=Decimal(data["o"]),
            high_price=Decimal(data["h"]),
            low_price=Decimal(data["l"]),
            total_ba_volume=Decimal(data["v"]),
            total_qa_volume=Decimal(data["q"]),
            total_trades=data["n"],
        )

tickers: dict[str, Ticker24hr] = {}