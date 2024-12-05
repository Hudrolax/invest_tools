# core/db.py
# init alembic
# init alembic: alembic init -t async alembic
# make migrations
# alembic revision --autogenerate -m "your message here"
import contextlib
from typing import Any, AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from core.config import DATABASE_URL


Base = declarative_base()


class DatabaseSessionManager:
    def __init__(self, host: str, engine_kwargs: dict[str, Any] = {}):
        self.engine = create_async_engine(host, pool_size=20, max_overflow=50, **engine_kwargs)
        self.sessionmaker = async_sessionmaker(
            autocommit=False, bind=self.engine)

    async def close(self):
        if self.engine is None:
            self.sessionmaker = None
            return

        await self.engine.dispose()

        self.engine = None
        self.sessionmaker = None

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        if self.engine is None:
            raise Exception("DatabaseSessionManager is not initialized")

        async with self.engine.begin() as connection:
            try:
                yield connection
            except Exception:
                await connection.rollback()
                raise

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self.sessionmaker is None:
            raise Exception("DatabaseSessionManager is not initialized")

        session = self.sessionmaker()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


sessionmanager = DatabaseSessionManager(DATABASE_URL, {"echo": False})


async def get_db():
    async with sessionmanager.session() as session:
        yield session
