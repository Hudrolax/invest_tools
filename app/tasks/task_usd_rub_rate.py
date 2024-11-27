import asyncio
from sqlalchemy.exc import NoResultFound
from core.db import DatabaseSessionManager
from brokers.investing_com.investing_com_api import get_rate
import logging
from datetime import datetime
from models.broker import BrokerORM
from models.symbol import SymbolORM

logger = logging.getLogger(__name__)

async def task_get_usd_rub_rate(
    stop_event: asyncio.Event,
    sessionmaker: DatabaseSessionManager,
) -> None:
    logger.info(f"start task: {logger.name}")

    broker_name = 'investing.com'
    symbol_name = 'USDRUB'
    while not stop_event.is_set():
        try:
            async with sessionmaker.session() as db:
                # check / add broker
                try:
                    broker = await BrokerORM.get_by_name(db, broker_name)
                except NoResultFound:
                    broker = await BrokerORM.create(db, name=broker_name)
                
                try:
                    symbol = await SymbolORM.get_by_name_and_broker(db, name=symbol_name, broker_name=broker_name)
                except NoResultFound:
                    symbol = await SymbolORM.create(db, name=symbol_name, broker_id=broker.id)

                rate = await get_rate('usd-rub')
                logger.info(f'usd-rub rate got from investing.com: {rate}')
                if rate:
                    await SymbolORM.update(db, id=symbol.id, rate=rate, last_update_time=datetime.now())
                else:
                    raise ValueError(f'rate usd-rub from investing.com is None (value: {rate})')

            await asyncio.sleep(60 * 60 * 24)
        except Exception as ex:
            logger.critical(str(ex))
            await asyncio.sleep(60)
