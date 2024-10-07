import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from utils import get_env_value


logging.disable(logging.WARNING)

LOG_FORMAT = '%(name)s (%(levelname)s) %(asctime)s: %(message)s'
DATE_FORMAT = '%d-%m-%y %H:%M:%S'
LOG_LEVEL = logging.WARNING

LOG_TO_FILE = True if os.getenv('LOG_TO_FILE') == 'true' else False

log_dir = 'logs'
log_file = 'log.txt'

handlers = []

formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
if LOG_TO_FILE:
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    handler = RotatingFileHandler(os.path.join(
        log_dir, log_file), maxBytes=2097152, backupCount=5)
    handler.setFormatter(formatter)
    handlers.append(handler)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
handlers.append(console_handler)

root_logger = logging.getLogger()
root_logger.setLevel(LOG_LEVEL)
root_logger.handlers = handlers


# DB settings
DB_HOST = get_env_value('DB_HOST')
DB_NAME = get_env_value('DB_NAME')
DB_USER = get_env_value('DB_USER')
DB_PASS = get_env_value('DB_PASS')
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"

# SECRET
SECRET = get_env_value('SECRET')

# Telegram bot API key
TELEGRAM_BOT_SECRET = get_env_value('TELEGRAM_BOT_SECRET')

# Binance
BINANCE_API_KEY = get_env_value('BINANCE_API_KEY')
BINANCE_API_SECRET = get_env_value('BINANCE_API_SECRET')

# Binance spot
BINANCE_SPOT_API = 'https://api.binance.com'
BINANCE_SPOT_WSS = 'wss://stream.binance.com'
BINANCE_SPOT_ORDER_URL = "/api/v3/order"
BINANCE_SPOT_CANCEL_ALL_ORDERS_URL = '/api/v3/allOpenOrders'
BINANCE_SPOT_LISTEN_KEY_URL = '/api/v3/listenKey'
BINANCE_SPOT_KLINES_URL = '/api/v3/klines'
BINANCE_SPOT_ACCOUNT_INFO_URL = '/api/v3/account'
BINANCE_SPOT_MARKET_INFO_URL = '/api/v3/exchangeInfo'
BINANCE_SPOT_OPEN_ORDERS_URL = '/api/v3/openOrders'

# Binance USD-M Futures
BINANCE_UM_API = 'https://fapi.binance.com'
BINANCE_UM_WSS = 'wss://fstream.binance.com'
BINANCE_UM_ORDER_URL = "/fapi/v3/order"
BINANCE_UM_CANCEL_ALL_ORDERS_URL = '/fapi/v3/allOpenOrders'
BINANCE_UM_LISTEN_KEY_URL = '/fapi/v3/listenKey'
BINANCE_UM_KLINES_URL = '/fapi/v3/klines'
BINANCE_UM_ACCOUNT_INFO_URL = '/fapi/v3/account'
BINANCE_UM_MARKET_INFO_URL = '/fapi/v3/exchangeInfo'
BINANCE_UM_OPEN_ORDERS_URL = '/fapi/v3/openOrders'

# Binance USD-C Futures
BINANCE_CM_API = 'https://dapi.binance.com'
BINANCE_CM_WSS = 'wss://dstream.binance.com'
BINANCE_CM_ORDER_URL = "/dapi/v3/order"
BINANCE_CM_CANCEL_ALL_ORDERS_URL = '/dapi/v3/allOpenOrders'
BINANCE_CM_LISTEN_KEY_URL = '/dapi/v3/listenKey'
BINANCE_CM_KLINES_URL = '/dapi/v3/klines'
BINANCE_CM_ACCOUNT_INFO_URL = '/dapi/v3/account'
BINANCE_CM_MARKET_INFO_URL = '/dapi/v3/exchangeInfo'
BINANCE_CM_OPEN_ORDERS_URL = '/dapi/v3/openOrders'

# Bybit WSS endpoints
BYBIT_WSS_SPOT = 'wss://stream.bybit.com/v5/public/spot'
BYBIT_WSS_PERPETUAL = 'wss://stream.bybit.com/v5/public/linear'
BYBIT_WSS_INVERSE = 'wss://stream.bybit.com/v5/public/inverse'

# OpenAI API key
OPENAI_API_KEY = get_env_value('OPENAI_API_KEY')
