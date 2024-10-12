class TickHandleError(Exception):
    pass


class OpenOrderError(TickHandleError):
    pass


class GetOrdersError(TickHandleError):
    pass


class CloseOrderError(TickHandleError):
    pass
