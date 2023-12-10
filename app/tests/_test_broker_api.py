import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound

from models.broker import BrokerORM
from models.symbol import SymbolORM
from models.alert import AlertORM

from conftest import new_user, new_broker, new_symbol, new_alert


@pytest.mark.asyncio
async def test_create_broker(client: AsyncClient, db_session: AsyncSession, token: str):
    headers = dict(TOKEN=token)

    # test unauthorized
    response = await client.post("/brokers/", json={"name": "Binance"})
    assert response.status_code == 401

    response = await client.post("/brokers/", headers=headers, json={"name": "Binance"})
    assert response.status_code == 200
    result = response.json()
    assert result["name"] == "Binance"

    # read the record from DB
    broker = await BrokerORM.get(db_session, id = result['id'])
    assert broker.id == result['id']

    # test fail when adds a double
    response = await client.post("/brokers/", headers=headers, json={"name": "Binance"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_read_broker(client: AsyncClient, db_session: AsyncSession):
    # read unexisting broker
    response = await client.get(f"/brokers/999")
    assert response.status_code == 404

    # add a new broker
    broker = await BrokerORM.create(db=db_session, name='Binance')
    response = await client.get(f"/brokers/{broker.id}")
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, dict)
    assert result['name'] == 'Binance'


@pytest.mark.asyncio
async def test_read_brokers(client: AsyncClient, db_session: AsyncSession):
    # check brokers is clear
    response = await client.get(f"/brokers/")
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert result == []

    # add two brokers
    broker1 = await BrokerORM.create(db=db_session, name='Binance')
    broker2 = await BrokerORM.create(db=db_session, name='Coinbase')

    response = await client.get(f"/brokers/")
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert result[0]['name'] == broker1.name
    assert result[1]['name'] == broker2.name


@pytest.mark.asyncio
async def test_update_broker(client: AsyncClient, db_session: AsyncSession):
    broker1 = await BrokerORM.create(db=db_session, name='Binance')
    broker2 = await BrokerORM.create(db=db_session, name='Coinbase')

    # update broker 1
    payload = dict(
        name = 'New broker'
    )
    response = await client.put(f"/brokers/{broker1.id}", json=payload)
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, dict)
    assert result['name'] == payload['name']

    # try to update with existing name
    payload = dict(
        name = 'Coinbase'
    )
    response = await client.put(f"/brokers/{broker1.id}", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_delete_broker(client: AsyncClient, db_session: AsyncSession):
    # test delete unexisting broker
    response = await client.delete(f"/brokers/{999}")
    assert response.status_code == 404

    broker1 = await BrokerORM.create(db=db_session, name='Binance')
    broker2 = await BrokerORM.create(db=db_session, name='Coinbase')

    response = await client.delete(f"/brokers/{broker1.id}")
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, bool)
    assert result == True

    brokers = await BrokerORM.get_all(db_session)
    assert len(brokers) == 1
    assert brokers[0] == broker2


    # test cascade deleting
    user = await new_user(db_session)
    broker = await new_broker(db_session, 'New broker')
    symbol = await new_symbol(db_session, broker_id=broker.id, name='New symbol') # type: ignore
    alert = await new_alert(db_session, user_id=user.id, symbol_id=symbol.id) # type: ignore

    response = await client.delete(f"/brokers/{broker.id}")
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, bool)
    assert result == True

    try:
        await SymbolORM.get(db_session, symbol.id) # type: ignore
        assert False
    except NoResultFound:
        assert True

    try:
        await AlertORM.get(db_session, alert.id) # type: ignore
        assert False
    except NoResultFound:
        assert True