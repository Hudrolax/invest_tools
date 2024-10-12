from typing import Literal

BybitBroker = Literal["Bybit-spot", "Bybit_perpetual", "Bybit-inverse"]
BYBIT_BROKERS = ["Bybit-spot", "Bybit_perpetual", "Bybit-inverse"]
BybitTimeframe = Literal[
    "1", "3", "5", "15", "30", "60", "120", "240", "360", "720", "D", "W", "M"
]
BybitStreamType = Literal["Ticker", "Kline", "Trade"]

ByitMarketType = Literal["linear", "inverse", "spot", "option"]
OrderFilter = Literal[
    "Order",  # Active order
    "StopOrder",  # conditional order for Futures and Spot,
    "tpslOrder",  # spot TP/SL order
    "OcoOrder",  # Spot oco order,
    "BidirectionalTpslOrder",  # Spot bidirectional TPSL order
]
OrderStatus = Literal[
    "New",
    "PartiallyFilled",
    "Untriggered",
    "Rejected",
    "PartiallyFilledCanceled",
    "Filled",
    "Cancelled",
    "Triggered",
    "Deactivated",
]
OpenOnly = Literal[
    0,  # (default): UTA2.0, UTA1.0, classic account query open status orders (e.g., New, PartiallyFilled) only
    1,  # UTA2.0, UTA1.0(except inverse)
    2,  # UTA1.0(inverse), classic account
]

bybit_symbols: dict[str, list[str]] = {
    "Bybit-spot": [],
    "Bybit_perpetual": [],
    "Bybit-inverse": [],
}

market_data: dict[str, dict] = {
    "Bybit-spot": {},
    "Bybit_perpetual": {},
    "Bybit-inverse": {},
}
