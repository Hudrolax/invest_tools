# import traceback
# import asyncio
# import aiohttp
# import json
# from core.config import (
#     WSS_FUTURES_URL,
#     BASE_FUTURES_URL,
#     BINANCE_API_KEY,
#     BINANCE_API_SECRET,
#     FUTURES_ORDER_URL,
#     FUTURES_CANCEL_ALL_ORDERS_URL,
#     FUTURES_KLINES_URL,
#     FUTURES_LISTEN_KEY_URL,
#     FUTURES_ACCOUNT_INFO_URL,
#     FUTURES_MARKET_INFO_URL,
#     FUTURES_OPEN_ORDERS_URL,
# )
# import logging
# import hashlib
# import hmac
# import time
# import urllib.parse
# from decimal import Decimal
# from ..exceptions import OpenOrderError, CloseOrderError, TickHandleError
# from typing import Callable, Literal

# logger = logging.getLogger(__name__)



# async def get_account_info(**kwargs) -> dict:
#     """The function gets account info

#     Returns:
#         dict: parsed JSON data
#     """
#     logger = logging.getLogger('account_info')
#     params = {
#         "timestamp": int(time.time() * 1000),  # Timestamp in milliseconds
#         **kwargs
#     }
#     response = await authorized_request(
#         FUTURES_ACCOUNT_INFO_URL, 'get', params, TickHandleError, logger)
#     if not isinstance(response, dict):
#         raise TypeError
#     return response


# async def modify_order(
#     order_id: int,
#     symbol: str,
#     side: str,
#     quantity: Decimal,
#     price: Decimal,
#     origClientOrderId:str = '',
#     **kwargs
# ) -> dict:
#     """The function modify the order

#     Args:
#         order_id (int): id of modifing order
#         symbol (str): Symbol, like BTCUSDT
#         side (str): BUY or SELL
#         quantity (Decimal): Quantity on base asset. For BTCUSDT it's amount of BTC
#         price (Decimal | None): price in quote asset. For BTCUSDT it's price in USDT. None - if type is None
#         origClientOrderId (str): client side order ID
#         order_type (str, optional): ORDER type. See types in official Binance documentation. Defaults to 'LIMIT'.
#         **kwargs: option kwargs. See official Binance documentation.

#     Returns:
#         dict: parsed JSON response
#     """
#     logger = logging.getLogger('modify_order')
#     try:
#         params = {
#             "orderId": order_id,
#             "origClientOrderId": origClientOrderId,
#             "symbol": symbol,
#             "side": side,
#             "quantity": str(quantity) if quantity >= 0 else str(abs(quantity)),
#             "price": str(price),
#             "recvWindow": 50000,
#             "timestamp": int(time.time() * 1000),  # Timestamp in milliseconds
#             **kwargs
#         }
#         response = await authorized_request(FUTURES_ORDER_URL, 'put', params, OpenOrderError, logger)
#     except Exception as e:
#         error_message = f"Exception occurred: {type(e).__name__}, {e.args}\n"
#         error_message += traceback.format_exc()
#         logger.critical(error_message)
#         raise e

#     if not isinstance(response, dict):
#         logger.error(f'Response not a dict. Response type {type(response)}')
#         raise OpenOrderError(
#             f'Response not a dict. Response type {type(response)}')
#     return response


# async def open_order(
#     symbol: str,
#     side: str,
#     quantity: Decimal,
#     price: Decimal | None = None,
#     order_type: str = 'LIMIT',
#     newClientOrderId: str = '',
#     **kwargs
# ) -> dict:
#     """The function opens an order

#     Args:
#         symbol (str): Symbol, like BTCUSDT
#         side (str): BUY or SELL
#         quantity (Decimal): Quantity on base asset. For BTCUSDT it's amount of BTC
#         price (Decimal | None): price in quote asset. For BTCUSDT it's price in USDT. None - if type is None
#         order_type (str, optional): ORDER type. See types in official Binance documentation. Defaults to 'LIMIT'.
#         **kwargs: option kwargs. See official Binance documentation.

#     Returns:
#         dict: parsed JSON response
#     """
#     logger = logging.getLogger('open_order')
#     try:
#         # order parameters
#         kwargs = dict(
#             price=str(price),
#             type=order_type,
#             timeInForce="GTC",
#             **kwargs
#         )
#         if order_type == 'MARKET':
#             del kwargs['price']
#             del kwargs['timeInForce']
        
#         if newClientOrderId != '':
#             kwargs['newClientOrderId'] = newClientOrderId

#         params = {
#             "recvWindow": 50000,
#             "symbol": symbol,
#             "side": side,
#             "quantity": str(quantity) if quantity >= 0 else str(abs(quantity)),
#             "timestamp": int(time.time() * 1000),  # Timestamp in milliseconds
#             **kwargs
#         }
#         response = await authorized_request(FUTURES_ORDER_URL, 'post', params, OpenOrderError, logger)
#     except OpenOrderError as e:
#         # error_message = f"Exception occurred: {type(e).__name__}, {e.args}\n"
#         # error_message += traceback.format_exc()
#         # logger.warning(error_message)
#         raise e

#     if not isinstance(response, dict):
#         logger.error(f'Response not a dict. Response type {type(response)}')
#         raise OpenOrderError(
#             f'Response not a dict. Response type {type(response)}')
#     return response


# async def cancel_order(symbol: str, order_id: int = -1, origClientOrderId: str = '', **kwargs) -> dict:
#     """The function cancels an order (not position)

#     Args:
#         symbol (str): symbol like BTCUSDT
#         order_id (int, optional): Order ID from Binance. Defaults to -1.
#         origClientOrderId (str, optional): Client side order ID. Defaults to ''.
#         **kwargs: option kwargs. See official Binance documentation.
#         !!! order_id or origClientOrderId - one of them MUST be filled.

#     Returns:
#         dict: parsed JSON response
#     """
#     logger = logging.getLogger('cancel_order')
#     # Параметры ордера
#     if order_id == -1 and origClientOrderId == '':
#         raise CloseOrderError('order_id or origClientOrderId must be sent.')

#     try:
#         params = {
#             "recvWindow": 50000,
#             "symbol": symbol,
#             "orderId": order_id,
#             "timestamp": int(time.time() * 1000),  # Timestamp in milliseconds
#             **kwargs
#         }
#         if order_id == -1:
#             del params['orderId']
#             params['origClientOrderId'] = origClientOrderId

#         response = await authorized_request(FUTURES_ORDER_URL, 'delete', params, CloseOrderError, logger)
#     except CloseOrderError as e:
#         # error_message = f"Exception occurred: {type(e).__name__}, {e.args}\n"
#         # error_message += traceback.format_exc()
#         # logger.critical(error_message)
#         raise e

#     if not isinstance(response, dict):
#         logger.error(f'Response no a dict. Response type {type(response)}')
#         raise CloseOrderError(
#             f'Response no a dict. Response type {type(response)}')
#     return response


# async def cancel_all_orders(symbol: str, **kwargs) -> bool:
#     """The function cancels all opened orders (not positions)

#     Args:
#         symbol (str): symbol like BTCUSDT

#     Returns:
#         bool: True, if all orders was cancelled.
#     """
#     logger = logging.getLogger('cancel_all_orders')
#     params = {
#         "recvWindow": 50000,
#         "symbol": symbol,
#         "timestamp": int(time.time() * 1000),  # Timestamp in milliseconds
#         **kwargs
#     }
#     response = await authorized_request(FUTURES_CANCEL_ALL_ORDERS_URL, 'delete', params, CloseOrderError, logger)
#     if not isinstance(response, dict):
#         logger.error(f'Response is not a dict. Response type {type(response)}')
#         raise CloseOrderError(
#             f'Response is not a dict. Response type {type(response)}')
#     return response['code'] == 200


# async def get_open_orders(symbol: str, **kwargs) -> list:
#     logger = logging.getLogger('get_open_orders')
#     params = {
#         "symbol": symbol,
#         "timestamp": int(time.time() * 1000),  # Timestamp in milliseconds
#         **kwargs
#     }
#     response = await authorized_request(FUTURES_OPEN_ORDERS_URL, 'get', params, TickHandleError, logger)
#     if not isinstance(response, list):
#         logger.error(f'Response is not a dict. Response type {type(response)}')
#         raise TickHandleError(
#             f'Response is not a dict. Response type {type(response)}')
#     return response






# async def get_listen_key(session: aiohttp.ClientSession) -> str:
#     """The function gets listen key for start user-data stream.

#     Args:
#         session (aiohttp.ClientSession): Session object

#     Returns:
#         str: the listen key
#     """
#     headers = {
#         "X-MBX-APIKEY": BINANCE_API_KEY,
#     }
#     url = BASE_FUTURES_URL + FUTURES_LISTEN_KEY_URL
#     async with session.post(url, headers=headers) as response:
#         data = await response.json()
#         return data['listenKey']


# async def keepalive_listen_key(session: aiohttp.ClientSession, listen_key: str):
#     """The function for keep alive listen key

#     Args:
#         session (aiohttp.ClientSession): the session
#         listen_key (str): exist listen key
#     """
#     headers = {
#         "X-MBX-APIKEY": BINANCE_API_KEY,
#     }
#     url = BASE_FUTURES_URL + FUTURES_LISTEN_KEY_URL
#     params = {
#         "listenKey": listen_key
#     }
#     await session.put(url, params=params, headers=headers)


# async def handle_stream(
#     session: aiohttp.ClientSession,
#     listen_key: str,
#     handler: Callable,
#     stop_event: asyncio.Event,
#     market: str,
#     logger: logging.Logger,
# ) -> None:
#     """User data stream handler

#     Args:
#         session (aiohttp.ClientSession): active session
#         listen_key (str): exist listen key
#         handler (Callable): data handler
#         stop_event (asyncio.Event): the stop event
#         market (str): maket name
#         logger (logging.Logger): actual logger
#     """
#     while not stop_event.is_set():
#         try:
#             wss_url = f"{WSS_FUTURES_URL}/ws/{listen_key}"
#             async with session.ws_connect(wss_url) as ws:
#                 async for msg in ws:
#                     # Handle received message
#                     logger.debug(msg)
#                     await handler(msg.json(), market)
#         except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK) as e:
#             logger.warning(
#                 f"Stream encountered an error: {e}. Reconnecting...")
#             await asyncio.sleep(1)
#         except Exception as e:
#             logger.error(
#                 f"Stream encountered an error: {e}.Reconnecting...")
#             await asyncio.sleep(1)


# async def run_user_data_stream(data_handler: Callable, stop_event: asyncio.Event, market: str):
#     """The function runs user-data stream

#     Args:
#         data_handler (Callable): user-data handler
#         stop_event (asyncio.Event): the stop event
#         market (str): market name
#     """
#     logger = logging.getLogger('user_data_stream')
#     async with aiohttp.ClientSession() as session:
#         listen_key = await get_listen_key(session)
#         logger.debug(f"Got listen key: {listen_key}")

#         # Launch the stream handler
#         handler = asyncio.create_task(
#             handle_stream(session, listen_key, data_handler, stop_event, market, logger))

#         while not stop_event.is_set():
#             await asyncio.sleep(60*50)  # 50 minutes

#             try:
#                 # Refresh listen key
#                 await keepalive_listen_key(session, listen_key)
#                 logger.debug("Refreshed listen key.")
#             except Exception as e:
#                 logger.warning(
#                     f"Failed to refresh listen key: {e}. Getting a new one...")
#                 listen_key = await get_listen_key(session)
#                 logger.debug(f"Got new listen key: {listen_key}")

#                 # Cancel the old handler and start a new one with the new listen key
#                 handler.cancel()
#                 await handler
#                 handler = asyncio.create_task(
#                     handle_stream(session, listen_key, data_handler, stop_event, market, logger))
