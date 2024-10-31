import os
import traceback
import logging
from datetime import datetime

def get_env_value(name: str) -> str:
    value = os.getenv(name)
    if value is None:
        raise ValueError(
            f'{name} environment variable should be filled in the OS.')
    return value


def async_traceback_errors(logger: logging.Logger | None = None, raise_error: bool = True):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if logger is not None:
                    error_message = f"Exception occurred: {type(e).__name__}, {e.args}\n"
                    error_message += traceback.format_exc()
                    logger.critical(error_message)
                if raise_error:
                    raise
        return wrapper
    return decorator

class StringNotUpperCaseError(Exception):
    """Исключение, выбрасываемое, когда строка не в верхнем регистре."""
    pass

def check_uppercase(s: str) -> None:
    """Проверяет, является ли строка строкой в верхнем регистре.

    Args:
        s (str): Строка для проверки.

    Raises:
        StringNotUpperCaseError: Если строка не в верхнем регистре.
    """
    if not s.isupper():
        raise StringNotUpperCaseError(f"Строка '{s}' не в верхнем регистре.")

