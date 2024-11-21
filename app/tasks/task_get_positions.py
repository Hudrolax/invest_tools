import asyncio
import logging

from sqlalchemy import select

from brokers.bybit.bybit_api import (
    get_position_info,
)
from models.broker import BrokerORM
from models.symbol import SymbolORM
from core.db import DatabaseSessionManager
from utils import async_traceback_errors
from handlers.positions import refresh_positions_in_db
from brokers.exceptions import GetPositionsError

logger = logging.getLogger(__name__)


@async_traceback_errors(logger=logger)
async def task_get_positions(
    stop_event: asyncio.Event,
    sessionmaker: DatabaseSessionManager,
) -> None:
    """
    Get positions once in N second. Base positions refresh handler working with WebSocket
    """
    logger = logging.getLogger("task_get_positons")
    logger.info(f"start task: {logger.name}")
    while not stop_event.is_set():
        try:
            async with sessionmaker.session() as db:
                for broker in ["Bybit_perpetual", "Bybit-inverse"]:
                    broker_symbols = (
                        (
                            await db.execute(
                                select(SymbolORM.name)
                                .select_from(SymbolORM)
                                .join(
                                    BrokerORM,
                                    (BrokerORM.id == SymbolORM.broker_id)
                                    & (BrokerORM.name == broker),
                                )
                                .where(SymbolORM.active_wss)
                            )
                        )
                        .mappings()
                        .all()
                    )
                    for symbol in broker_symbols:
                        positions: list[dict] = await get_position_info(broker, symbol["name"])  # type: ignore
                        positions = [
                            pos for pos in positions if pos["positionValue"] != ""
                        ]
                        await refresh_positions_in_db(db, positions, broker, symbol["name"])  # type: ignore
                        await asyncio.sleep(0.5)
                    await asyncio.sleep(1)

            await asyncio.sleep(120)
        except GetPositionsError as ex:
            logger.error(f"Error in task_get_positions: {str(ex)}")
            await asyncio.sleep(120)
        except Exception as ex:
            logger.error(f"Error in task_get_positions: {str(ex)}")
            await asyncio.sleep(120)
