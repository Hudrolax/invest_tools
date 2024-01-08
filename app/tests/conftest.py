# tests/conftest.py
from httpx import AsyncClient
import asyncio
from sqlalchemy import text
import pytest
from contextlib import ExitStack

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from datetime import datetime
from asyncpg import Connection
from typing import AsyncGenerator, Any

from main import app as actual_app
from core.db import Base, sessionmanager, get_db, DatabaseSessionManager
from core.config import DB_HOST, DB_USER, DB_PASS

from models.user import UserORM
from models.broker import BrokerORM
from models.symbol import SymbolORM
from models.alert import AlertORM
from models.token import TokenORM

from brokers.binance import binance_symbols

from routers import create_access_token

binance_symbols['Binance-spot'].append('BTCUSDT')
binance_symbols['Binance-spot'].append('BTCRUB')
binance_symbols['Binance-spot'].append('BTCARS')
binance_symbols['Binance-spot'].append('ETHUSDT')
binance_symbols['Binance-spot'].append('USDTRUB')
binance_symbols['Binance-spot'].append('USDTARS')


async def new_broker(db_session: AsyncSession, name: str = 'Binance-spot') -> BrokerORM:
    return await BrokerORM.create(db=db_session, name=name)


async def new_user(
    db_session: AsyncSession,
    username: str = 'John Doe',
    password: str = '123',
    telegram_id: int = 123,
    email: str = 'user@example.com',
    name: str = 'user'
) -> UserORM:
    return await UserORM.create(
        db=db_session,
        username=username,
        password=password,
        telegram_id=telegram_id,
        email=email,
        name=name,
    )


async def make_user(
    db: AsyncSession,
    username: str = 'test',
    password: str = '123',
    telegram_id: int = 123,
    email: str = 'user@example.com',
    token: str = '123',
    name: str = 'user',
) -> tuple[UserORM, TokenORM]:
    user = await UserORM.create(db, username=username, password=password, telegram_id=telegram_id, email=email, name=name)
    token = await TokenORM.create(db, user_id=user.id, token='123', description='new token')
    return user, token


async def new_symbol(
    db_session: AsyncSession,
    name: str = 'BTCUSDT',
    broker_id: int = 1,
) -> SymbolORM:
    return await SymbolORM.create(db=db_session, name=name, broker_id=broker_id)


async def new_alert(
    db_session: AsyncSession,
    symbol_name: str = 'BTCUSDT',
    broker_name: str = 'Binance-spot',
    user_id: int = 1,
    price: Decimal = Decimal('12.75'),
    trigger: str = 'above',
    created_at: datetime = datetime.now(),
    triggered_at: datetime | None = None,
    is_active: bool = True,
    is_sent: bool = False,
) -> AlertORM:
    return await AlertORM.create(
        db=db_session,
        symbol_name=symbol_name,
        broker_name=broker_name,
        user_id=user_id,
        price=price,
        trigger=trigger,
        created_at=created_at,
        triggered_at=triggered_at,
        is_active=is_active,
        is_sent=is_sent,
    )

# test base name and URL
test_db_name = 'test_db'
TEST_DATABASE_URL = f"postgresql+asyncpg://{
    DB_USER}:{DB_PASS}@{DB_HOST}/{test_db_name}"


@pytest.fixture(autouse=True)
def app():
    """Fixture for wrapping an app"""
    with ExitStack():
        yield actual_app


@pytest.fixture(scope="session")
def event_loop():
    """
    # Custom event loop fixture
    # ***************************
    # You should to make pytest.ini file in the app dir of your project with content:
    [pytest]
    asyncio_mode = auto
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


def run_migrations(connection: Connection) -> None:
    """Make migrations"""
    config = Config("alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    script = ScriptDirectory.from_config(config)

    def upgrade(rev, context):
        return script._upgrade_revs("head", rev)

    context = MigrationContext.configure(
        connection, opts={"target_metadata": Base.metadata, "fn": upgrade}) # type: ignore

    with context.begin_transaction():
        with Operations.context(context):
            context.run_migrations()


@pytest.fixture(scope="session", autouse=True)
async def setup_database() -> AsyncGenerator[DatabaseSessionManager, Any]:
    # Run alembic migrations on test DB
    async with sessionmanager.connect() as connection:
        await connection.execute(text('COMMIT'))
        # Попытка удалить базу данных
        await connection.execute(text(f'DROP DATABASE IF EXISTS {test_db_name}'))
        await connection.execute(text(f'CREATE DATABASE {test_db_name}'))

    # make a new sessionmanager
    test_sessionmanager = DatabaseSessionManager(TEST_DATABASE_URL)

    # Run alembic migrations on test DB
    async with test_sessionmanager.connect() as connection:
        await connection.run_sync(run_migrations)

    try:
        yield test_sessionmanager
    finally:
        await test_sessionmanager.close()

    # drop test DB after testing
    async with sessionmanager.connect() as connection:
        await connection.execute(text('COMMIT'))
        # Попытка удалить базу данных
        await connection.execute(text(f'DROP DATABASE IF EXISTS {test_db_name}'))

    await sessionmanager.close()


@pytest.fixture(scope="function", autouse=True)
async def db_session(setup_database) -> AsyncGenerator[AsyncSession, Any]:
    async with setup_database.session() as session:
        try:
            # yield session instance
            yield session

        finally:
            #  Clear DB after testing
            await session.rollback()
            # # Turn off the foreign key constraint checks for DB cleaning,
            # await session.execute(text("SET CONSTRAINTS ALL DEFERRED;"))

            # # Iterate through all tables and clear data
            # for table_name in reversed(Base.metadata.sorted_tables):
            #     await session.execute(text(f"TRUNCATE TABLE {table_name.name} RESTART IDENTITY CASCADE;"))

            # # Turn on the foreign key constraint checks
            # await session.execute(text("SET CONSTRAINTS ALL IMMEDIATE;"))

            # await session.commit()


@pytest.fixture(scope="function", autouse=True)
async def session_override(app, db_session) -> None:
    """Overriding session generator in the app"""
    async def get_db_session_override():
        """Generator with test session"""
        yield db_session

    app.dependency_overrides[get_db] = get_db_session_override


@pytest.fixture(scope="function")
async def client(app) -> AsyncGenerator[AsyncClient, Any]:
    """Async client for testing an API"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def token(db_session: AsyncSession):
    user = await new_user(db_session, username='Authorized user', email='authorized@example.com')
    token = await TokenORM.create(db_session, user_id=user.id, token='test_token', description='test token')
    yield token.token


@pytest.fixture
async def jwt_token(db_session: AsyncSession):
    user = await new_user(db_session, username='Authorized user', email='authorized@example.com')
    token = create_access_token(user.to_dict())
    yield token, user


@pytest.fixture
async def symbols(db_session: AsyncSession):
    broker = await BrokerORM.get_by_name(db_session, name='Binance-spot')
    await SymbolORM.create(db_session, name='BTCUSDT', broker_id=broker.id, rate=Decimal('43000'))
    await SymbolORM.create(db_session, name='BTCARS', broker_id=broker.id, rate=Decimal('40536000'))
    await SymbolORM.create(db_session, name='BTCRUB', broker_id=broker.id, rate=Decimal('3875000'))
    await SymbolORM.create(db_session, name='USDTRUB', broker_id=broker.id, rate=Decimal('94.82'))
    await SymbolORM.create(db_session, name='USDTARS', broker_id=broker.id, rate=Decimal('980.25'))
