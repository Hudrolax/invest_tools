import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from datetime import datetime

from core.config import TELEGRAM_BOT_SECRET
from .conftest import make_user, new_alert

from models.broker import BrokerORM


@pytest.mark.asyncio
async def test_create_alert(client: AsyncClient, db_session: AsyncSession):
    broker = (await BrokerORM.get_all(db_session))[0]
    user, token = await make_user(db_session)
    payload = dict(
        symbol_name='BTCUSDT',
        broker_name=broker.name,
        price='12.75',
        trigger='above',
    )
    response = await client.post("/alerts/", json=payload)
    assert response.status_code == 401

    headers = dict(TOKEN=token.token)
    response = await client.post("/alerts/", headers=headers, json=payload) # type: ignore
    assert response.status_code == 200

    result = response.json() 
    assert result['price'] == payload['price']
    assert result['trigger'] == payload['trigger']
    assert result['triggered_at'] == None
    assert result['is_active'] == True
    assert result['is_sent'] == False


@pytest.mark.asyncio
async def test_create_alert_via_telegram_api(client: AsyncClient, db_session: AsyncSession):
    broker = (await BrokerORM.get_all(db_session))[0]
    user, token = await make_user(db_session, telegram_id=123456789)
    payload = dict(
        symbol_name='BTCUSDT',
        broker_name=broker.name,
        price='12.75',
        trigger='above',
    )
    headers = {'TBOT-SECRET': TELEGRAM_BOT_SECRET, 'TELEGRAM-ID': '123456789'}
    response = await client.post("/alerts/", headers=headers, json=payload) # type: ignore
    assert response.status_code == 200

    result = response.json() 
    assert result['user_id'] == user.id
    assert result['price'] == payload['price']
    assert result['trigger'] == payload['trigger']
    assert result['triggered_at'] == None
    assert result['is_active'] == True
    assert result['is_sent'] == False

@pytest.mark.asyncio
async def test_create_alert_wrong_broker(client: AsyncClient, db_session: AsyncSession):
    user, token = await make_user(db_session)
    headers: dict[str, str] = dict(TOKEN=token.token) # type: ignore

    payload = dict(
        symbol_name='BTCUSDT',
        broker_name='sdfjjj',
        price='12.75',
        trigger='above',
    )
    response = await client.post("/alerts/", headers=headers, json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_alert_wrong_price(client: AsyncClient, db_session: AsyncSession):
    broker = (await BrokerORM.get_all(db_session))[0]
    user, token = await make_user(db_session)
    headers: dict[str, str] = dict(TOKEN=token.token) # type: ignore

    # wrong price
    payload = dict(
        symbol_name='BTCUSDT',
        broker_name=broker.name,
        price='0',
        trigger='above',
    )
    response = await client.post("/alerts/", headers=headers, json=payload)
    assert response.status_code == 422

    broker = (await BrokerORM.get_all(db_session))[0]
    user, token = await make_user(db_session, username='user2', email='user2@example.com', telegram_id=1234)
    headers: dict[str, str] = dict(TOKEN=token.token) # type: ignore
    payload = dict(
        symbol_name='BTCUSDT',
        broker_name=broker.name,
        price='-3000.3',
        trigger='above',
    )
    response = await client.post("/alerts/", headers=headers, json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_alert_wrong_triger(client: AsyncClient, db_session: AsyncSession):
    broker = (await BrokerORM.get_all(db_session))[0]
    user, token = await make_user(db_session)
    headers: dict[str, str] = dict(TOKEN=token.token) # type: ignore

    # wrong trigger
    payload = dict(
        symbol_name='BTCUSDT',
        broker_name=broker.name,
        price='12.75',
        trigger='djvndkjnf',
    )
    response = await client.post("/alerts/", headers=headers, json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_alert(client: AsyncClient, db_session: AsyncSession):
    broker = (await BrokerORM.get_all(db_session))[0]
    response = await client.put(f"/alerts/{999}", json=dict(price='12.99'))
    assert response.status_code == 401

    user, token = await make_user(db_session)
    alert = await new_alert(db_session, user_id=user.id, symbol_name='BTCUSDT', broker_name=broker.name, price='99.99') # type: ignore

    headers: dict[str, str] = dict(TOKEN=token.token) # type: ignore
    payload = dict(
        price='1000.2',
        is_sent=True,
        is_active=False
    )
    response = await client.put(f"/alerts/{alert.id}", headers=headers, json=payload)
    assert response.status_code == 200
    result = response.json()
    for key in payload.keys():
        assert result[key] == payload[key]

    response = await client.put(f"/alerts/{alert.id}", json=payload)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_read_alert(client: AsyncClient, db_session: AsyncSession):
    # test read unexisted alert
    broker = (await BrokerORM.get_all(db_session))[0]
    response = await client.get(f"/alerts/{999}")
    assert response.status_code == 401

    user, token = await make_user(db_session)
    alert = await new_alert(db_session, user_id=user.id, symbol_name='BTCUSDT', broker_name=broker.name, price='99.99') # type: ignore

    headers: dict[str, str] = dict(TOKEN=token.token) # type: ignore
    response = await client.get(f"/alerts/{alert.id}", headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert result['id'] == alert.id
    assert result['user_id'] == user.id

    response = await client.get(f"/alerts/{999}", headers=headers)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_read_alerts(client: AsyncClient, db_session: AsyncSession):
    broker = (await BrokerORM.get_all(db_session))[0]
    response = await client.get(f"/alerts/")
    assert response.status_code == 401

    user, token = await make_user(db_session)
    user2, token2 = await make_user(db_session, username='user2', telegram_id=321, email='dd@ff.com', token='321')
    alert1 = await new_alert(db_session, user_id=user.id, broker_name=broker.name, symbol_name='BTCUSDT', price=Decimal('123')) # type: ignore
    alert2 = await new_alert(db_session, user_id=user.id, broker_name=broker.name, symbol_name='BTCUSDT', price=Decimal('999')) # type: ignore
    alert3 = await new_alert(db_session, user_id=user2.id, broker_name=broker.name, symbol_name='BTCUSDT', price=Decimal('999')) # type: ignore

    headers: dict[str, str] = dict(TOKEN=token.token) # type: ignore
    response = await client.get(f"/alerts/", headers=headers)
    assert response.status_code == 200
    result = response.json()
    for i in range(1):
        for key in result[i].keys():
            val = getattr(locals()[f'alert{i+1}'], key)
            if isinstance(val, Decimal):
                assert Decimal(result[i][key]) == val
            elif isinstance(val, datetime):
                assert result[i][key] == val.isoformat()
            else:
                assert result[i][key] == val

    await alert2.update(db_session, id=alert2.id, is_sent=True, is_active=False, triggered_at=datetime.now()) # type: ignore
    response = await client.get(f"/alerts/", headers=headers, params=dict(is_sent=True))
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]['id'] == alert2.id


@pytest.mark.asyncio
async def test_read_alerts_via_telegram_api(client: AsyncClient, db_session: AsyncSession):
    broker = (await BrokerORM.get_all(db_session))[0]
    response = await client.get(f"/alerts/telegram_bot_api/")
    assert response.status_code == 401

    user, token = await make_user(db_session)
    user2, token2 = await make_user(db_session, username='user2', telegram_id=321, email='dd@ff.com', token='321')
    alert1 = await new_alert(db_session, user_id=user.id, broker_name=broker.name, symbol_name='BTCUSDT', price=Decimal('123')) # type: ignore
    alert2 = await new_alert(db_session, user_id=user.id, broker_name=broker.name, symbol_name='BTCUSDT', price=Decimal('999')) # type: ignore
    alert3 = await new_alert(
        db_session,
        user_id=user2.id, # type: ignore
        broker_name=broker.name, # type: ignore
        symbol_name='BTCUSDT',
        triggered_at=datetime.now(),
        price=Decimal('999'),
    )

    headers: dict[str, str] = {'TBOT-SECRET': TELEGRAM_BOT_SECRET} # type: ignore
    response = await client.get(f"/alerts/telegram_bot_api/", headers=headers, params=dict(is_triggered=True))
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]['id'] == alert3.id


@pytest.mark.asyncio
async def test_delete_alert(client: AsyncClient, db_session: AsyncSession):
    broker = (await BrokerORM.get_all(db_session))[0]
    response = await client.delete(f"/alerts/{999}")
    assert response.status_code == 401

    user, token = await make_user(db_session)
    alert = await new_alert(db_session, user_id=user.id, broker_name=broker.name, symbol_name='BTCUSDT') # type: ignore

    headers: dict[str, str] = dict(TOKEN=token.token) # type: ignore
    response = await client.delete(f"/alerts/{alert.id}", headers=headers)
    assert response.status_code == 200
    assert response.json() == True

    response = await client.delete(f"/alerts/{alert.id}", headers=headers)
    assert response.status_code == 404
