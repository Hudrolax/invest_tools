class TickHandleError(Exception):
    pass

class OpenOrderError(TickHandleError):
    pass

class GetOrdersError(TickHandleError):
    pass

class GetPositionsError(TickHandleError):
    pass

class ModifyOrderError(TickHandleError):
    pass

class CloseOrderError(TickHandleError):
    pass

class GetSymbolsInfo(TickHandleError):
    pass

class GetAccountInfoError(TickHandleError):
    pass
