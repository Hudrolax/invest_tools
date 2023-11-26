import pytest
from decimal import Decimal
from datetime import datetime
from tests.unit.fixtures import (
    db_setup,
)
from models.brokers import add_broker
from models.symbols import add_symbol
from models.users import add_user
from models.alerts import (
    add_alert,
    delete_alert,
    read_alert,
    read_alerts,
    update_alert,
    delete_alert,
)
from models.exceptions import NotFoundError


@pytest.mark.asyncio
async def test_add_and_read_alert(db_setup) -> None:
    """Test adding and reading an alert into DB."""
    async for conn in db_setup:
        broker_id = await add_broker(
            conn=conn,
            name='new broker'
        )
        symbol_id = await add_symbol(conn, 'BTCUSDT', broker_id)
        user_id = await add_user(conn, name='user1', telegram_id=123)
        alert_id = await add_alert(conn, user_id=user_id, symbol_id=symbol_id, price=Decimal('33.2'), trigger='above')
        res = await read_alert(conn, alert_id)
        assert res is not None
        assert res['symbol_id'] == symbol_id
        assert res['user_id'] == user_id
        assert res['symbol_id'] == symbol_id
        assert res['is_active'] == True
        assert res['trigger'] == 'above'
        assert res['triggered'] == False
        assert res['is_sent'] == False
        assert isinstance(res['created_at'], datetime)
        assert res['triggered_at'] is None
        assert res['price'] == Decimal('33.2')


@pytest.mark.asyncio
async def test_reading_alerts(db_setup) -> None:
    """Test reading alerts into DB."""
    async for conn in db_setup:
        broker_id = await add_broker(
            conn=conn,
            name='new broker'
        )
        symbol_id = await add_symbol(conn, 'BTCUSDT', broker_id)
        user_id = await add_user(conn, name='user1', telegram_id=123)
        alert_id1 = await add_alert(conn, user_id=user_id, symbol_id=symbol_id, price=Decimal('33.2'), trigger='above')
        alert_id2 = await add_alert(conn, user_id=user_id, symbol_id=symbol_id, price=Decimal('35.123456789'), trigger='above')

        res = await read_alerts(conn, user_id=user_id)
        assert res is not None
        assert isinstance(res, list)
        assert len(res) == 2
        assert res[0]['id'] == alert_id1
        assert res[0]['user_id'] == user_id
        assert res[0]['price'] == Decimal('33.2')
        assert res[1]['id'] == alert_id2
        assert res[1]['user_id'] == user_id
        assert res[1]['price'] == Decimal('35.123456789')


@pytest.mark.asyncio
async def test_updating_alert(db_setup) -> None:
    """Test updating an alert into DB."""
    async for conn in db_setup:
        broker_id = await add_broker(
            conn=conn,
            name='new broker'
        )
        symbol_id = await add_symbol(conn, 'BTCUSDT', broker_id)
        user_id = await add_user(conn, name='user1', telegram_id=123)
        alert_id = await add_alert(conn, user_id=user_id, symbol_id=symbol_id, price=Decimal('33.2'), trigger='above')

        res = await read_alert(conn, id=alert_id)
        assert res is not None
        assert res['price'] == Decimal('33.2')

        await update_alert(conn, id=alert_id, price=Decimal('333'))
        res = await read_alert(conn, id=alert_id)
        assert res is not None
        assert res['price'] == Decimal('333')


@pytest.mark.asyncio
async def test_deleting_alert(db_setup) -> None:
    """Test deleting an alert into DB."""
    async for conn in db_setup:
        broker_id = await add_broker(
            conn=conn,
            name='new broker'
        )
        symbol_id = await add_symbol(conn, 'BTCUSDT', broker_id)
        user_id = await add_user(conn, name='user1', telegram_id=123)
        alert_id = await add_alert(conn, user_id=user_id, symbol_id=symbol_id, price=Decimal('33.2'), trigger='above')

        res = await read_alert(conn, id=alert_id)
        assert res is not None

        await delete_alert(conn, alert_id)
        try:
            await read_alert(conn, id=alert_id)
        except NotFoundError:
            pass