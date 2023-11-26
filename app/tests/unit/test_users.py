import pytest
from tests.unit.fixtures import (
    db_setup,
)
from models.users import (
      add_user,
      read_user,
      read_users,
      update_user
)


@pytest.mark.asyncio
async def test_add_user(db_setup) -> None:
    """Test adding a user to DB."""
    async for conn in db_setup:
        await add_user(conn, 'Test Name', 123456789, 'test@example.com')
        result = await conn.fetchrow("SELECT * FROM users")
        assert result is not None
        assert result['name'] == 'Test Name'
        assert result['telegram_id'] == 123456789
        assert result['email'] == 'test@example.com'


@pytest.mark.asyncio
async def test_read_user(db_setup) -> None:
    """Test reading a user from DB."""
    async for conn in db_setup:
        user_id = await add_user(conn, 'Test Name', 123456789, 'test@example.com')
        result = await read_user(conn, user_id)
        assert result is not None
        assert result['name'] == 'Test Name'
        assert result['telegram_id'] == 123456789
        assert result['email'] == 'test@example.com'


@pytest.mark.asyncio
async def test_read_users(db_setup) -> None:
    """Test reading users from DB."""
    async for conn in db_setup:
        await add_user(conn, 'Test Name1', 123456789, 'test1@example.com')
        await add_user(conn, 'Test Name2', 1234567890, 'test2@example.com')
        result = await read_users(conn)
        assert result is not None
        assert isinstance(result, list)
        assert result[0]['name'] == 'Test Name1'
        assert result[1]['name'] == 'Test Name2'
        assert result[0]['telegram_id'] == 123456789
        assert result[1]['telegram_id'] == 1234567890
        assert result[0]['email'] == 'test1@example.com'
        assert result[1]['email'] == 'test2@example.com'


@pytest.mark.asyncio
async def test_update_user(db_setup) -> None:
    """Test updating a user into DB."""
    async for conn in db_setup:
        user_id = await add_user(conn, 'Test Name', 123456789, 'test@example.com')
        await update_user(conn, user_id, name='New name', email='new@example.com')
        result = await read_user(conn, user_id)
        assert result is not None
        assert result['name'] == 'New name'
        assert result['telegram_id'] == 123456789
        assert result['email'] == 'new@example.com'

        try:
            await update_user(conn, user_id)
        except ValueError:
            pass