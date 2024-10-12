import logging
from brokers.bybit import ByitMarketType, OrderFilter, OpenOnly, OrderStatus
from utils import check_uppercase
from ..exceptions import GetOrdersError
from ..requests import authorized_request


logger = logging.getLogger("bybit-api")


async def get_orders(
    category: ByitMarketType,
    symbol: str | None = None,
    openOnly: OpenOnly | None = None,
    orderFilter: OrderFilter | None = None,
    orderId: str | None = None,
    orderLinkId: str | None = None,
    limit: int | None = 50,
) -> list:
    params = {
        "category": category,
        **({"symbol": symbol} if symbol else {}),
        **({"openOnly": openOnly} if openOnly is not None else {}),
        **({"orderFilter": orderFilter} if orderFilter is not None else {}),
        **({"orderId": orderId} if orderId is not None else {}),
        **({"orderLinkId": orderLinkId} if orderLinkId is not None else {}),
        **({"limit": limit} if limit else {}),
    }

    if symbol:
        check_uppercase(symbol)

    response = await authorized_request(
        broker="Bybit-inverse",
        endpoint="/order/realtime",
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
                broker="Bybit-inverse",
                endpoint="/order/realtime",
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
    category: ByitMarketType,
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
        "category": category,
        **({"symbol": symbol} if symbol else {}),
        **({"orderId": orderId} if orderId is not None else {}),
        **({"orderLinkId": orderLinkId} if orderLinkId is not None else {}),
        **({"orderFilter": orderFilter} if orderFilter is not None else {}),
        **({"orderStatus": orderStatus} if orderStatus is not None else {}),
        **({"startTime": startTime} if startTime is not None else {}),
        **({"endTime": endTime} if endTime is not None else {}),
        **({"limit": limit} if limit else {}),
    }

    if symbol:
        check_uppercase(symbol)

    response = await authorized_request(
        broker="Bybit-inverse",
        endpoint="/order/history",
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
                broker="Bybit-inverse",
                endpoint="/order/history",
                http_method="GET",
                params=params,
                ErrorClass=GetOrdersError,
                logger=logger,
            )
            orders = [*orders, *response["result"]["list"]]

        return orders
    else:
        raise GetOrdersError(response)
