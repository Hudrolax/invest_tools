import asyncio
import logging
from brokers.bybit import (
    BybitBroker,
    ByitMarketType,
    OrderFilter,
    OpenOnly,
    OrderStatus,
    OrderSide,
    OrderType,
    MarketUnit,
    TriggerDirection,
    TriggerBy,
)
from ..exceptions import (
    GetOrdersError,
    CloseOrderError,
    GetPositionsError,
    ModifyOrderError,
    OpenOrderError,
    GetSymbolsInfo,
    GetAccountInfoError,
)
from ..requests import authorized_request, unauthorizrd_request


logger = logging.getLogger("bybit-api")


def convert_broker_to_category(broker: BybitBroker) -> ByitMarketType:
    if broker == "Bybit-spot":
        return "spot"
    elif broker == "Bybit_perpetual":
        return "linear"
    elif broker == "Bybit-inverse":
        return "inverse"


async def get_orders(
    broker: BybitBroker,
    symbol: str | None = None,
    openOnly: OpenOnly | None = None,
    orderFilter: OrderFilter | None = None,
    orderId: str | None = None,
    orderLinkId: str | None = None,
    limit: int | None = 50,
) -> list:
    params = {
        "category": convert_broker_to_category(broker),
        **({"symbol": symbol.upper()} if symbol else {}),
        **({"openOnly": openOnly} if openOnly is not None else {}),
        **({"orderFilter": orderFilter} if orderFilter is not None else {}),
        **({"orderId": orderId} if orderId is not None else {}),
        **({"orderLinkId": orderLinkId} if orderLinkId is not None else {}),
        **({"limit": limit} if limit else {}),
    }

    endpoint = "/order/realtime"

    response = await authorized_request(
        broker=broker,
        endpoint=endpoint,
        http_method="GET",
        params=params,
        ErrorClass=GetOrdersError,
        logger=logger,
    )

    if response.get("retMsg") == "OK":
        orders = response["result"]["list"]
        while response["result"].get("nextPageCursor"):
            await asyncio.sleep(0.2)
            params["cursor"] = response["result"].get("nextPageCursor")
            response = await authorized_request(
                broker=broker,
                endpoint=endpoint,
                http_method="GET",
                params=params,
                ErrorClass=GetOrdersError,
                logger=logger,
            )
            # print('next cursor ', response['result'].get('nextPageCursor'))
            # print(response)
            orders = [*orders, *response["result"]["list"]]

        return orders
    else:
        raise GetOrdersError(response)


async def get_order_history(
    broker: BybitBroker,
    symbol: str | None = None,
    orderFilter: OrderFilter | None = None,
    orderStatus: OrderStatus | None = None,
    orderId: str | None = None,
    orderLinkId: str | None = None,
    startTime: int | None = None,
    endTime: int | None = None,
    limit: int | None = 50,
) -> list:
    params = {
        "category": convert_broker_to_category(broker),
        **({"symbol": symbol.upper()} if symbol else {}),
        **({"orderId": orderId} if orderId is not None else {}),
        **({"orderLinkId": orderLinkId} if orderLinkId is not None else {}),
        **({"orderFilter": orderFilter} if orderFilter is not None else {}),
        **({"orderStatus": orderStatus} if orderStatus is not None else {}),
        **({"startTime": startTime} if startTime is not None else {}),
        **({"endTime": endTime} if endTime is not None else {}),
        **({"limit": limit} if limit else {}),
    }

    endpoint = "/order/history"

    response = await authorized_request(
        broker=broker,
        endpoint=endpoint,
        http_method="GET",
        params=params,
        ErrorClass=GetOrdersError,
        logger=logger,
    )

    if response.get("retMsg") == "OK":
        orders = response["result"]["list"]
        while response["result"].get("nextPageCursor"):
            await asyncio.sleep(0.2)
            params["cursor"] = response["result"].get("nextPageCursor")
            response = await authorized_request(
                broker=broker,
                endpoint=endpoint,
                http_method="GET",
                params=params,
                ErrorClass=GetOrdersError,
                logger=logger,
            )
            orders = [*orders, *response["result"]["list"]]

        return orders
    else:
        raise GetOrdersError(response)


async def cancel_order(
    broker: BybitBroker,
    symbol: str,
    orderId: str | None = None,
    orderLinkId: str | None = None,
    orderFilter: OrderFilter | None = None,
) -> bool:
    params = {
        "category": convert_broker_to_category(broker),
        **({"symbol": symbol.upper()} if symbol else {}),
        **({"orderId": orderId} if orderId is not None else {}),
        **({"orderLinkId": orderLinkId} if orderLinkId is not None else {}),
        **({"orderFilter": orderFilter} if orderFilter is not None else {}),
    }

    response = await authorized_request(
        broker=broker,
        endpoint="/order/cancel",
        http_method="POST",
        params=params,
        ErrorClass=CloseOrderError,
        logger=logger,
    )

    if response.get("retMsg") == "OK":
        return True
    else:
        raise CloseOrderError(response)


async def modify_order(
    broker: BybitBroker,
    symbol: str,
    orderId: str | None = None,
    orderLinkId: str | None = None,
    qty: str | None = None,
    price: str | None = None,
) -> bool:
    params = {
        "category": convert_broker_to_category(broker),
        **({"symbol": symbol.upper()} if symbol else {}),
        **({"orderId": orderId} if orderId is not None else {}),
        **({"orderLinkId": orderLinkId} if orderLinkId is not None else {}),
        **({"qty": qty} if qty is not None else {}),
        **({"price": price} if price is not None else {}),
    }

    response = await authorized_request(
        broker=broker,
        endpoint="/order/amend",
        http_method="POST",
        params=params,
        ErrorClass=ModifyOrderError,
        logger=logger,
    )

    if response.get("retMsg") == "OK":
        return True
    else:
        raise ModifyOrderError(response)


async def open_order(
    broker: BybitBroker,
    symbol: str,
    side: OrderSide,
    orderType: OrderType,
    qty: str,
    price: str | None = None,
    marketUnit: MarketUnit | None = None,
    isLeverage: int | None = None,
    orderLinkId: str | None = None,
    triggerDirection: TriggerDirection | None = None,
    triggerPrice: str | None = None,
    triggerBy: TriggerBy | None = None,
    takeProfit: str | None = None,
    stopLoss: str | None = None,
    tpTriggerBy: TriggerBy | None = None,
    slTriggerBy: TriggerBy | None = None,
) -> bool:

    params = {
        "category": convert_broker_to_category(broker),
        **({"symbol": symbol.upper()} if symbol else {}),
        **({"side": side} if side else {}),
        **({"orderType": orderType} if orderType is not None else {}),
        **({"qty": qty} if qty is not None else {}),
        **({"price": price} if price is not None else {}),
        **({"marketUnit": marketUnit} if marketUnit is not None else {}),
        **({"isLeverage": isLeverage} if isLeverage is not None else {}),
        **({"orderLinkId": orderLinkId} if orderLinkId is not None else {}),
        **({"triggerDirection": triggerDirection} if triggerDirection is not None else {}),
        **({"triggerPrice": triggerPrice} if triggerPrice is not None else {}),
        **({"triggerBy": triggerBy} if triggerBy is not None else {}),
        **({"takeProfit": takeProfit} if takeProfit is not None else {}),
        **({"stopLoss": stopLoss} if stopLoss is not None else {}),
        **({"tpTriggerBy": tpTriggerBy} if tpTriggerBy is not None else {}),
        **({"slTriggerBy": slTriggerBy} if slTriggerBy is not None else {}),
    }

    response = await authorized_request(
        broker=broker,
        endpoint="/order/create",
        http_method="POST",
        params=params,
        ErrorClass=OpenOrderError,
        logger=logger,
    )

    if response.get("retMsg") == "OK":
        return True
    else:
        raise OpenOrderError(response)


async def get_position_info(
    broker: BybitBroker,
    symbol: str | None = None,
) -> list[dict]:
    params = {
        "category": convert_broker_to_category(broker),
        **({"symbol": symbol.upper()} if symbol else {}),
    }
    endpoint = "/position/list"

    response = await authorized_request(
        broker=broker,
        endpoint=endpoint,
        http_method="GET",
        params=params,
        ErrorClass=GetPositionsError,
        logger=logger,
    )

    if response.get("retMsg") == "OK":
        positions = response["result"]["list"]
        while response["result"].get("nextPageCursor"):
            await asyncio.sleep(0.2)
            params["cursor"] = response["result"].get("nextPageCursor")
            response = await authorized_request(
                broker=broker,
                endpoint=endpoint,
                http_method="GET",
                params=params,
                ErrorClass=GetPositionsError,
                logger=logger,
            )
            positions = positions + response["result"]["list"]

        return positions
    else:
        raise GetPositionsError(response)


async def get_symbols_info(
    broker: BybitBroker,
) -> list[dict]:
    params = {
        "category": convert_broker_to_category(broker),
    }
    endpoint = "/market/instruments-info"

    response = await unauthorizrd_request(
        broker=broker,
        endpoint=endpoint,
        http_method="GET",
        params=params,
        logger=logger,
    )

    if response.get("retMsg") == "OK":
        symbols = response["result"]["list"]
        while response["result"].get("nextPageCursor"):
            await asyncio.sleep(0.2)
            params["cursor"] = response["result"].get("nextPageCursor")
            response = await unauthorizrd_request(
                broker=broker,
                endpoint=endpoint,
                http_method="GET",
                params=params,
                logger=logger,
            )
            symbols = symbols + response["result"]["list"]

        return symbols
    else:
        raise GetSymbolsInfo(response)


async def get_fee_rate(
    broker: BybitBroker,
    symbol: str | None = None,
) -> list[dict]:
    params = {
        "category": convert_broker_to_category(broker),
        **({"symbol": symbol.upper()} if symbol else {}),
    }
    endpoint = "/account/fee-rate"

    response = await authorized_request(
        broker=broker,
        endpoint=endpoint,
        http_method="GET",
        params=params,
        ErrorClass=GetAccountInfoError,
        logger=logger,
    )

    if response.get("retMsg") == "OK":
        symbols = response["result"]["list"]
        while response["result"].get("nextPageCursor"):
            await asyncio.sleep(0.2)
            params["cursor"] = response["result"].get("nextPageCursor")
            response = await authorized_request(
                broker=broker,
                endpoint=endpoint,
                http_method="GET",
                params=params,
                ErrorClass=GetAccountInfoError,
                logger=logger,
            )
            symbols = symbols + response["result"]["list"]

        return symbols
    else:
        raise GetAccountInfoError(response)
