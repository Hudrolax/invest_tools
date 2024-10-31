import logging
from brokers.bybit import BybitBroker, ByitMarketType, OrderFilter, OpenOnly, OrderStatus
from ..exceptions import GetOrdersError, CloseOrderError, GetPositionsError
from ..requests import authorized_request


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

    endpoint="/order/realtime"

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

    endpoint="/order/history"

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
        ErrorClass=GetOrdersError,
        logger=logger,
    )

    if response.get("retMsg") == "OK":
        return True
    else:
        raise CloseOrderError(response)


async def get_position_info(
    broker: BybitBroker,
    symbol: str | None = None,
) -> list[dict]:
    params = {
        "category": convert_broker_to_category(broker),
        **({"symbol": symbol.upper()} if symbol else {}),
    }
    endpoint = '/position/list'

    response = await authorized_request(
        broker=broker,
        endpoint=endpoint,
        http_method="GET",
        params=params,
        ErrorClass=GetOrdersError,
        logger=logger,
    )

    if response.get("retMsg") == "OK":
        positions = response["result"]["list"]
        while response["result"].get("nextPageCursor"):
            params["cursor"] = response["result"].get("nextPageCursor")
            response = await authorized_request(
                broker=broker,
                endpoint=endpoint,
                http_method="GET",
                params=params,
                ErrorClass=GetOrdersError,
                logger=logger,
            )
            positions = positions + response["result"]["list"]

        return positions
    else:
        raise GetPositionsError(response)
