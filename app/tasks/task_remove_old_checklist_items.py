import asyncio
import logging
from datetime import datetime, timedelta, UTC

from core.db import DatabaseSessionManager
from models.checklist import ChecklistORM


logger = logging.getLogger(__name__)


async def task_remove_old_checklist_items(
    stop_event: asyncio.Event,
    sessionmaker: DatabaseSessionManager,
) -> None:
    init = True
    logger = logging.getLogger('task_remove_old_checklist_items')
    logger.info(f'start task: {logger.name}')
    while not stop_event.is_set():
        async with sessionmaker.session() as db:
            try:
                items = await ChecklistORM.get_items_after_date(db, date=datetime.now(UTC) - timedelta(days=180))
                for item in items:
                    await db.delete(item)
                    await db.flush()

                init = False
            except Exception as ex:
                logger.critical(str(ex))
                if not init:
                    await asyncio.sleep(300)
                    continue
                else:
                    await asyncio.sleep(3)
                    continue
        await asyncio.sleep(86400)
