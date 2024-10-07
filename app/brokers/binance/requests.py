import traceback
import asyncio
import logging
import aiohttp
import hashlib
import hmac
import time
import json
import urllib.parse
from typing import Callable

from ..exceptions import TickHandleError
from . import BinanceBroker
from core.config import (
    BINANCE_API_SECRET,
    BINANCE_API_KEY,

    BINANCE_SPOT_API,
    BINANCE_UM_API,
    BINANCE_CM_API,
)


async def unauthorizrd_request(
    broker: BinanceBroker,
    endpoint: str,
    http_method: str,
    params: dict,
    logger: logging.Logger,
) -> dict:
    """The function makes unauthorized request

    Args:
        endpoint (str): endpoint to request
        http_method (str): request method (like get, post)
        params (dict): params for request
        logger (logging.Logger): actual logger
        stop (asyncio.Event): stop Event for stopping attempts

    Returns:
        dict: parsed JSON response
    """
    for _ in range(5):  # do 5 attempts
        try:
            if broker == 'Binance-spot':
                url = BINANCE_SPOT_API + endpoint
            elif broker == 'Binance-UM-Futures':
                url = BINANCE_UM_API + endpoint
            elif broker == 'Binance-CM-Futures':
                url = BINANCE_CM_API + endpoint
            
            async with aiohttp.ClientSession() as session:
                async with session.request(http_method, url, params=params) as response:
                    response.raise_for_status()  # проверка на ошибки HTTP
                    text = await response.text()
                    logger.debug(f"raw response: {text}")
                    return json.loads(text)

        except aiohttp.ClientError as e:
            logger.warning(f"An error occurred: {e}")
            await asyncio.sleep(2)  # pause before next attemption
        except Exception as e:
            error_message = f"Exception occurred: {type(e).__name__}, {e.args}\n"
            error_message += traceback.format_exc()
            logger.critical(error_message)
            raise TickHandleError(f'unexpected error {e}')

    raise aiohttp.ClientError("Connection error.")


async def authorized_request(
    broker: BinanceBroker,
    endpoint: str,
    http_method: str,
    params: dict,
    ErrorClass: Callable,
    logger: logging.Logger,
) -> dict | list:
    """The function makes authorized request to API (trades)

    Args:
        endpoint (str): request endpoint
        http_method (str): HTTP method (post, delete)
        params (dict): params for request
        ErrorClass (Callable): Error class for raising an error
        logger (logging.Logger): logger object for correct logging

    Returns:
        dict: parsed JSON response from the broker
    """
    if broker == 'Binance-spot':
        url = BINANCE_SPOT_API + endpoint
    elif broker == 'Binance-UM-Futures':
        url = BINANCE_UM_API + endpoint
    elif broker == 'Binance-CM-Futures':
        url = BINANCE_CM_API + endpoint

    # make the signature
    query_string = urllib.parse.urlencode(params)
    signature = hmac.new(str(BINANCE_API_SECRET).encode(),
                         query_string.encode(), hashlib.sha256).hexdigest()
    params["signature"] = signature

    headers = {
        "X-MBX-APIKEY": BINANCE_API_KEY
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(http_method, url, params=params, headers=headers) as response:
                response.raise_for_status()  # проверка на ошибки HTTP
                text = await response.text()
                logger.debug(f"response: {text}")
                return json.loads(text)
    except aiohttp.ClientResponseError as e:
        logger.error(
            f"An error occurred: {str(e)}, status code: {e.status}, message: {e.message}")
        raise ErrorClass(f'{e}')
    except aiohttp.ClientError as e:
        logger.warning(f"An error occurred: {str(e)}")
        raise ErrorClass(f'{e}')
    except Exception as e:
        error_message = f"Exception occurred: {type(e).__name__}, {e.args}\n"
        error_message += traceback.format_exc()
        logger.critical(error_message)
        raise ErrorClass(f'unexpected error {e}')
