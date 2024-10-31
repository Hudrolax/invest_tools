import asyncio
import logging
from sqlalchemy.exc import OperationalError
from sqlalchemy.future import select
from core.db import sessionmanager

logger = logging.getLogger(__name__)
root_logger = logging.getLogger()
root_logger.setLevel(logging.WARNING)


async def wait_for_db():
    num_retries = 60
    wait_time = 1

    print("\033[32mWait for DB was ready.")
    for i in range(num_retries):
        try:
            # Выполняем простой запрос, чтобы проверить жива ли база
            async with sessionmanager.session() as session:
                await session.execute(select(1))
                print("\n\033[32mDB is ready!\033[0m")
                return
        except (OperationalError, ConnectionRefusedError) as exc:
            logger.warning(f"DB not ready yet: {exc}")
            print(".", end="", flush=True)
            await asyncio.sleep(wait_time)
        except Exception as exc:
            logger.exception(f"Unexpected error while waiting for DB: {exc}")
            raise
        finally:
            await sessionmanager.close()

    logger.error(
        f"\033[31mCouldn't connect to database after {num_retries} attempts, exiting...\033[0m")
    exit(1)

if __name__ == '__main__':
    asyncio.run(wait_for_db())
