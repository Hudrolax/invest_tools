import pytest
from httpx import AsyncClient
from decimal import Decimal
from datetime import datetime, timezone

from main import app
from db.db_connection import db
from tests.unit.fixtures import db_setup
from models.symbols import add_symbol
from models.users import add_user
from models.brokers import add_broker
from models.alerts import (
    add_alert,
    read_alert,
)


@pytest.mark.asyncio
async def test_add_alert(db_setup):
    """Test adding an alert"""
    async for conn in db_setup:
        app.dependency_overrides[db.get_conn] = lambda: conn

        async with AsyncClient(app=app, base_url="http://test") as ac:
            broker_id = await add_broker(conn, 'Binance')
            symbol_id = await add_symbol(conn, 'BTCUSDT', broker_id)
            user_id = await add_user(conn, 'Hudro', telegram_id=123)

            payload = dict(
                symbol_id=symbol_id,
                user_id=user_id,
                price='12.75',
                trigger='above',
            )

            response = await ac.post("/alerts/", json=payload)
            assert response.status_code == 200

            # check response
            data = response.json()
            assert data['symbol_id'] == payload['symbol_id']
            assert data['user_id'] == payload['user_id']
            assert Decimal(data['price']) == Decimal(payload['price'])
            assert data['trigger'] == payload['trigger']
            assert isinstance(datetime.strptime(data['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ'), datetime)
            assert data['triggered_at'] is None
            assert data['is_active'] == True
            assert data['is_sent'] == False
            assert isinstance(data['id'], int)

            # check DB data
            alert = await read_alert(conn, data['id'])
            assert alert['id'] == data['id']
            assert alert['symbol_id'] == payload['symbol_id']
            assert alert['user_id'] == payload['user_id']
            assert Decimal(alert['price']) == Decimal(payload['price'])
            assert alert['trigger'] == payload['trigger']
            assert isinstance(datetime.strptime(data['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ'), datetime)
            assert alert['triggered_at'] is None
            assert alert['is_active'] == True
            assert alert['is_sent'] == False


@pytest.mark.asyncio
async def test_update_alert(db_setup):
    """Test updating an alert"""
    async for conn in db_setup:
        app.dependency_overrides[db.get_conn] = lambda: conn

        async with AsyncClient(app=app, base_url="http://test") as ac:
            broker_id = await add_broker(conn, 'Binance')
            symbol_id = await add_symbol(conn, 'BTCUSDT', broker_id)
            user_id = await add_user(conn, 'Hudro', telegram_id=123)
            alert_id = await add_alert(conn, user_id, symbol_id, Decimal('12.75'), 'above')

            triggered_date = datetime.now(timezone.utc)
            payload = dict(
                price = '12.35',
                triggered_at = triggered_date.isoformat(),
            )

            response = await ac.put(f"/alerts/{alert_id}", json=payload)
            assert response.status_code == 200

            data = response.json()
            assert Decimal(data['price']) == Decimal(payload['price'])
            assert datetime.fromisoformat(data['triggered_at']) == triggered_date

            alert = await read_alert(conn, alert_id)
            assert Decimal(alert['price']) == Decimal(payload['price'])
            assert alert['triggered_at'] == triggered_date


@pytest.mark.asyncio
async def test_get_alerts(db_setup):
    """Test getting alerts list"""
    async for conn in db_setup:
        app.dependency_overrides[db.get_conn] = lambda: conn

        async with AsyncClient(app=app, base_url="http://test") as ac:
            broker_id = await add_broker(conn, 'Binance')
            symbol_id = await add_symbol(conn, 'BTCUSDT', broker_id)
            user_id = await add_user(conn, 'Hudro', telegram_id=123)
            await add_alert(conn, user_id, symbol_id, Decimal('12.75'), 'above')
            await add_alert(conn, user_id, symbol_id, Decimal('15'), 'above')

            response = await ac.get(f"/alerts/", params={'user_id': user_id})
            assert response.status_code == 200
            data = response.json()

            assert isinstance(data['alerts'], list)
            assert len(data['alerts']) == 2
            assert Decimal(data['alerts'][0]['price']) == Decimal('12.75')
            assert Decimal(data['alerts'][1]['price']) == Decimal('15')


@pytest.mark.asyncio
async def test_get_alert(db_setup):
    """Test getting an alert"""
    async for conn in db_setup:
        app.dependency_overrides[db.get_conn] = lambda: conn

        async with AsyncClient(app=app, base_url="http://test") as ac:
            broker_id = await add_broker(conn, 'Binance')
            symbol_id = await add_symbol(conn, 'BTCUSDT', broker_id)
            user_id = await add_user(conn, 'Hudro', telegram_id=123)
            alert_id = await add_alert(conn, user_id, symbol_id, Decimal('12.75'), 'above')

            response = await ac.get(f"/alerts/{alert_id}")
            assert response.status_code == 200
            data = response.json()

            assert Decimal(data['price']) == Decimal('12.75')


@pytest.mark.asyncio
async def test_delete_alert(db_setup):
    """Test deleting an alert"""
    async for conn in db_setup:
        app.dependency_overrides[db.get_conn] = lambda: conn

        async with AsyncClient(app=app, base_url="http://test") as ac:
            broker_id = await add_broker(conn, 'Binance')
            symbol_id = await add_symbol(conn, 'BTCUSDT', broker_id)
            user_id = await add_user(conn, 'Hudro', telegram_id=123)
            alert_id = await add_alert(conn, user_id, symbol_id, Decimal('12.75'), 'above')

            response = await ac.delete(f"/alerts/{alert_id}")
            assert response.status_code == 200
            data = response.json()
            
            assert data['message'] == 'ok'