import asyncio
import logging

from brokers.binance import binance_symbols, market_data
from brokers.binance.market_data import get_market_info

logger = logging.getLogger(__name__)


async def task_update_market_data(
    stop_event: asyncio.Event,
) -> None:
    while not stop_event.is_set():
        try:
            for broker in binance_symbols.keys():
                market_data[broker] = await get_market_info(broker=broker)  # type: ignore
                symbols = market_data[broker]['symbols']
                binance_symbols[broker] = []
                for symbol in symbols:
                    binance_symbols[broker].append(symbol['symbol'])

            await asyncio.sleep(1200)
        except Exception as ex:
            logger.critical(str(ex))
            await asyncio.sleep(60)
