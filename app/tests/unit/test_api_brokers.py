import pytest
from httpx import AsyncClient
from main import app
from db.db_connection import db
from tests.unit.fixtures import db_setup
from models.brokers import (
    read_broker,
    read_brokers,
    add_broker,
)


@pytest.mark.asyncio
async def test_add_broker(db_setup):
    async for conn in db_setup:
        app.dependency_overrides[db.get_conn] = lambda: conn

        async with AsyncClient(app=app, base_url="http://test") as ac:
            payload = dict(
                name = 'test_broker'
            )

            response = await ac.post("/brokers/", json=payload)
            assert response.status_code == 200

            data = response.json()
            assert data['name'] == payload['name']
            assert isinstance(data['id'], int)

            data = await read_broker(conn, id=data['id'])
            assert data['name'] == payload['name']

            # test add exist broker
            response = await ac.post("/brokers/", json=payload)
            assert response.status_code == 422



@pytest.mark.asyncio
async def test_get_broker(db_setup):
    async for conn in db_setup:
        app.dependency_overrides[db.get_conn] = lambda: conn

        async with AsyncClient(app=app, base_url="http://test") as ac:
            broker_id = await add_broker(conn, name='test_broker')

            # get broker
            response = await ac.get(f"/brokers/{broker_id}")
            assert response.status_code == 200
            data = response.json()
            assert data['name'] == 'test_broker'
            assert data['id'] == broker_id


@pytest.mark.asyncio
async def test_get_brokers(db_setup):
    async for conn in db_setup:
        app.dependency_overrides[db.get_conn] = lambda: conn

        async with AsyncClient(app=app, base_url="http://test") as ac:
            broker_id1 = await add_broker(conn, name='broker1')
            broker_id2 = await add_broker(conn, name='broker2')

            # get brokers
            response = await ac.get(f"/brokers/")
            assert response.status_code == 200
            brokers = response.json()['brokers']
            assert isinstance(brokers, list)
            assert len(brokers) == 2
            assert brokers[0]['id'] == broker_id1
            assert brokers[0]['name'] == 'broker1'
            assert brokers[1]['id'] == broker_id2
            assert brokers[1]['name'] == 'broker2'


@pytest.mark.asyncio
async def test_update_broker(db_setup):
    async for conn in db_setup:
        app.dependency_overrides[db.get_conn] = lambda: conn

        async with AsyncClient(app=app, base_url="http://test") as ac:
            # add broker
            broker_id = await add_broker(conn, name='broker1')

            # update broker
            payload = dict(
                name = 'new broker name'
            )
            response = await ac.put(f"/brokers/{broker_id}", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data['name'] == payload['name']

            # test rename broker to exists name
            broker_id = await add_broker(conn, name='broker2')
            response = await ac.put(f"/brokers/{broker_id}", json=payload)
            assert response.status_code == 422



@pytest.mark.asyncio
async def test_delete_broker(db_setup):
    async for conn in db_setup:
        app.dependency_overrides[db.get_conn] = lambda: conn

        async with AsyncClient(app=app, base_url="http://test") as ac:
            # add broker
            broker_id = await add_broker(conn, name='broker1')

            # delete broker
            response = await ac.delete(f"/brokers/{broker_id}")
            assert response.status_code == 200
            data = response.json()
            assert data['message'] == 'ok'

            # try to delete unknown broker
            response = await ac.delete(f"/brokers/{999}")
            assert response.status_code == 404

            brokers = await read_brokers(conn)
            assert len(brokers) == 0
