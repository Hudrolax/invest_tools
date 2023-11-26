class ParamsError(Exception):
    def __init__(self, message: str = "") -> None:
        self.message = message
        super().__init__(self.message)


class NotFoundError(Exception):
    def __init__(self, message: str = "") -> None:
        self.message = message
        super().__init__(self.message)


class UniqueViolationError(Exception):
    def __init__(self, message: str = "") -> None:
        self.message = message
        super().__init__(self.message)