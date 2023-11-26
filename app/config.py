import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from utils import get_env_value


LOG_FORMAT = '%(name)s (%(levelname)s) %(asctime)s: %(message)s'
DATE_FORMAT = '%d-%m-%y %H:%M:%S'
LOG_LEVEL = logging.INFO

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