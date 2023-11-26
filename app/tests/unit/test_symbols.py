import pytest
from decimal import Decimal
from tests.unit.fixtures import (
    db_setup,
)
from models.brokers import add_broker
from models.symbols import (
    add_symbol,
    read_symbol,
    read_symbols,
    update_symbol,
    delete_symbol,
)
from models.users import add_user
from models.alerts import add_alert


@pytest.mark.asyncio
async def test_add_symbol(db_setup) -> None:
    """Test adding a symbol into DB."""
    async for conn in db_setup:
        broker_id = await add_broker(
            conn=conn,
            name='new broker'
        )
        symbol = await add_symbol(conn, name='BTCUSDT', broker_id=broker_id)
        result = await conn.fetchrow("SELECT * FROM symbols")
        assert result is not None
        assert result['name'] == 'BTCUSDT'


@pytest.mark.asyncio
async def test_read_symbol(db_setup) -> None:
    """Test reading a symbol from DB."""
    async for conn in db_setup:
        broker_id = await add_broker(
            conn=conn,
            name='new broker'
        )
        symbol = await add_symbol(conn, name='BTCUSDT', broker_id=broker_id)
        result = await read_symbol(conn, symbol)
        assert result is not None
        assert result['name'] == 'BTCUSDT'


@pytest.mark.asyncio
async def test_read_symbols(db_setup) -> None:
    """Test reading symbols from DB."""
    async for conn in db_setup:
        broker_id = await add_broker(
            conn=conn,
            name='new broker'
        )
        await add_symbol(conn, name='BTCUSDT', broker_id=broker_id)
        await add_symbol(conn, name='ETHUSDT', broker_id=broker_id)
        result = await read_symbols(conn)
        assert result is not None
        assert isinstance(result, list)
        assert result[0]['name'] == 'BTCUSDT'
        assert result[1]['name'] == 'ETHUSDT'


@pytest.mark.asyncio
async def test_update_symbol(db_setup) -> None:
    """Test updating a symbol into DB."""
    async for conn in db_setup:
        broker_id = await add_broker(
            conn=conn,
            name='new broker'
        )
        symbol = await add_symbol(conn, 'BTCUSDT', broker_id)
        await update_symbol(conn, symbol, name='ETHUSDT')
        result = await read_symbol(conn, symbol)
        assert result is not None
        assert result['name'] == 'ETHUSDT'
        assert result['broker_id'] == broker_id


@pytest.mark.asyncio
async def test_delete_symbol(db_setup) -> None:
    """Test updating a symbol into DB."""
    async for conn in db_setup:
        broker_id = await add_broker(
            conn=conn,
            name='new broker'
        )
        symbol_id = await add_symbol(conn, 'BTCUSDT', broker_id)
        result = await read_symbol(conn, symbol_id)
        assert result is not None
        assert result['name'] == 'BTCUSDT'

        # test cascade deleting
        user_id = await add_user(conn, name='user1', telegram_id=123)
        alert_id = await add_alert(conn, user_id=user_id, symbol_id=symbol_id, price=Decimal('33.2'), trigger='above')
        
        await delete_symbol(conn, broker_id)

        symbol = await conn.fetchrow('SELECT id FROM symbols WHERE id = $1', symbol_id)
        assert symbol is None

        alert = await conn.fetchrow('SELECT id FROM alerts WHERE id = $1', alert_id)
        assert alert is None