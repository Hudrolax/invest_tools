import pytest
from decimal import Decimal
from tests.unit.fixtures import (
    db_setup,
)
from models.brokers import (
    add_broker,
    read_broker,
    read_brokers,
    delete_broker,
)
from models.alerts import add_alert
from models.users import add_user
from models.symbols import add_symbol

@pytest.mark.asyncio
async def test_add_broker(db_setup) -> None:
    """Test adding a broker into DB."""
    async for conn in db_setup:
        await add_broker(
            conn=conn,
            name='new broker'
        )
        result = await conn.fetchrow("SELECT * FROM brokers")
        assert result is not None
        assert result['name'] == 'new broker'


@pytest.mark.asyncio
async def test_read_broker(db_setup) -> None:
    """Test reading a broker from DB."""
    async for conn in db_setup:
        broker_id = await add_broker(
            conn=conn,
            name='new broker'
        )
        result = await read_broker(conn, broker_id)
        assert result['name'] == 'new broker'


@pytest.mark.asyncio
async def test_read_brokers(db_setup) -> None:
    """Test reading a broker from DB."""
    async for conn in db_setup:
        # add two brokers
        await add_broker(conn, 'new broker1')
        await add_broker(conn, 'new broker2')
        result = await read_brokers(conn)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]['name'] == 'new broker1'
        assert result[1]['name'] == 'new broker2'


@pytest.mark.asyncio
async def test_delete_broker(db_setup) -> None:
    """Test deleting a broker from DB."""
    async for conn in db_setup:
        # add two brokers
        broker1_id = await add_broker(conn, 'new broker1')
        broker2_id = await add_broker(conn, 'new broker2')
        brokers = await conn.fetch("SELECT * FROM brokers ORDER BY id")
        assert brokers is not None
        assert len(brokers) == 2

        # delete first broker
        await delete_broker(conn, id=broker1_id)

        brokers = await conn.fetch("SELECT * FROM brokers ORDER BY id")
        assert brokers is not None
        assert len(brokers) == 1
        assert brokers[0]['id'] == broker2_id

        # test cascade deleting
        user_id = await add_user(conn, name='user1', telegram_id=123)
        symbol_id = await add_symbol(conn, name='BTCUSDT', broker_id=broker2_id)
        alert_id = await add_alert(conn, user_id=user_id, symbol_id=symbol_id, price=Decimal('33.2'), trigger='above')
        
        await delete_broker(conn, broker2_id)

        symbol = await conn.fetchrow('SELECT id FROM symbols WHERE id = $1', symbol_id)
        assert symbol is None

        alert = await conn.fetchrow('SELECT id FROM alerts WHERE id = $1', alert_id)
        assert alert is None
