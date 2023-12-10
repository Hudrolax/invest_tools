import logging

from . import BinanceBrokers
from .requests import unauthorizrd_request

from core.config import (
    BINANCE_SPOT_KLINES_URL,
    BINANCE_UM_KLINES_URL,
    BINANCE_CM_KLINES_URL,

    BINANCE_SPOT_MARKET_INFO_URL,
    BINANCE_UM_MARKET_INFO_URL,
    BINANCE_CM_MARKET_INFO_URL,
)


async def get_klines(
    broker: str,
    symbol: str,
    interval: str,
    limit: int = 500,
) -> dict:
    """The function gets klines history from Binance

    Args:
        symbol (str): symbol like BTCUSDT
        interval (str): interval (timeframe) like '15m'
        stop (asyncio.Event): stop event from the bot
        limit (int, optional): limit of klines. Defaults to 500.

    Returns:
        dict: parsed JSON response
    """

    logger = logging.getLogger('get_klines')
    params = {
        'symbol': symbol.upper(),
        'interval': interval,
        'limit': limit,
    }
    
    if broker == 'Binance-spot':
        url = BINANCE_SPOT_KLINES_URL
    elif broker == 'Binance-UM-Futures':
        url = BINANCE_UM_KLINES_URL
    elif broker == 'Binance-CM-Futures':
        url = BINANCE_CM_KLINES_URL
    else:
        raise ValueError(f'Wrong broker {broker}')

    return await unauthorizrd_request(broker, url, 'get', params, logger)


async def get_market_info(broker: str) -> dict:
    """The function gets exchange info (symbols, limits)

    Args:
        brokers (BinanceBrokers): Binance brokers enum

    Returns:
        dict: parsed JSON data
    """
    logger = logging.getLogger('get_market_info')
    if broker == 'Binance-spot':
        url = BINANCE_SPOT_MARKET_INFO_URL
    elif broker == 'Binance-UM-Futures':
        url = BINANCE_UM_MARKET_INFO_URL
    elif broker == 'Binance-CM-Futures':
        url = BINANCE_CM_MARKET_INFO_URL
    else:
        raise ValueError(f'Wrong broker {broker}')

    return await unauthorizrd_request(broker, url, 'get', {}, logger)