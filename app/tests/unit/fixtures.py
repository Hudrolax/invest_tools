import pytest
import asyncpg
import uuid
from apply_migrations import apply_migrations
from config import DB_HOST, DB_NAME, DB_USER, DB_PASS


@pytest.fixture
async def db_setup():
    """Fixture for making temp db for tests

    Yields:
        Generator[asyncpg.Connection]: Generator with connection to db
    """
    test_db_name = 'test_db_' + uuid.uuid4().hex
    conn = await asyncpg.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME)
    await conn.execute(f'DROP DATABASE IF EXISTS {test_db_name}')
    await conn.execute(f'CREATE DATABASE {test_db_name}')
    await conn.close()
    # connect to test_db
    conn = await asyncpg.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=test_db_name)
    # apply migrations
    await apply_migrations(conn)
    # return the connection (generator)
    try:
        yield conn
    finally:
        try:
            await conn.close()
        except:
            pass
        try:
            # connect to primary database for drop temp test db
            conn = await asyncpg.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME)
            await conn.execute(f'DROP DATABASE IF EXISTS {test_db_name}')
        finally:
            await conn.close()
