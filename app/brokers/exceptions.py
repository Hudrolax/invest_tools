class TickHandleError(Exception):
    pass


class OpenOrderError(TickHandleError):
    pass


class GetOrdersError(TickHandleError):
    pass


class GetPositionsError(TickHandleError):
    pass

class CloseOrderError(TickHandleError):
    pass
