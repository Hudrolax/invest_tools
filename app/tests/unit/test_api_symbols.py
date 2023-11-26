import pytest
from httpx import AsyncClient
from main import app
from db.db_connection import db
from tests.unit.fixtures import db_setup
from models.brokers import add_broker
from models.symbols import add_symbol, read_symbol, read_symbols
from models.exceptions import NotFoundError


@pytest.mark.asyncio
async def test_add_symbol(db_setup):
    async for conn in db_setup:
        app.dependency_overrides[db.get_conn] = lambda: conn

        async with AsyncClient(app=app, base_url="http://test") as ac:
            # add symbol without broker
            payload = dict(
                name='BTCUSDT',
            )
            response = await ac.post("/symbols/", json=payload)
            assert response.status_code == 422

            broker_id = await add_broker(conn, 'Binance')

            # add exists symbol
            await add_symbol(conn, name='BTCUSDT', broker_id=broker_id)

            payload = dict(
                name='BTCUSDT',
                broker_id=broker_id,
            )
            response = await ac.post("/symbols/", json=payload)
            assert response.status_code == 422


@pytest.mark.asyncio
async def test_read_symbol(db_setup):
    async for conn in db_setup:
        app.dependency_overrides[db.get_conn] = lambda: conn
        broker_id = await add_broker(conn, 'Binance')
        symbol_id = await add_symbol(conn, name='BTCUSDT', broker_id=broker_id)

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get(f"/symbols/{symbol_id}")
            assert response.status_code == 200

            res = response.json()
            assert res['name'] == 'BTCUSDT'

            # get unknown symbol
            response = await ac.get(f"/symbols/{999}")
            assert response.status_code == 404


@pytest.mark.asyncio
async def test_read_symbols(db_setup):
    async for conn in db_setup:
        app.dependency_overrides[db.get_conn] = lambda: conn
        broker_id = await add_broker(conn, 'Binance')
        await add_symbol(conn, name='BTCUSDT', broker_id=broker_id)
        await add_symbol(conn, name='ETHUSDT', broker_id=broker_id)

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get(f"/symbols/")
            assert response.status_code == 200

            res = response.json()['symbols']
            assert isinstance(res, list)

            assert res[0]['name'] == 'BTCUSDT'
            assert res[1]['name'] == 'ETHUSDT'


@pytest.mark.asyncio
async def test_update_symbols(db_setup):
    async for conn in db_setup:
        app.dependency_overrides[db.get_conn] = lambda: conn
        broker_id = await add_broker(conn, 'Binance')
        symbol_id = await add_symbol(conn, name='BTCUSDT', broker_id=broker_id)

        async with AsyncClient(app=app, base_url="http://test") as ac:
            payload = dict(
                name = 'ETHUSDT',
                broker_id = broker_id,
            )
            response = await ac.put(f"/symbols/{symbol_id}", json=payload)
            assert response.status_code == 200
            res_json = response.json()

            res = await read_symbol(conn, id=symbol_id)
            assert res['name'] == res_json['name']

            # update unkown symbol
            response = await ac.put(f"/symbols/{999}", json=payload)
            assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_symbols(db_setup):
    async for conn in db_setup:
        app.dependency_overrides[db.get_conn] = lambda: conn
        broker_id = await add_broker(conn, 'Binance')
        symbol_id1 = await add_symbol(conn, name='BTCUSDT', broker_id=broker_id)
        symbol_id2 = await add_symbol(conn, name='ETHUSDT', broker_id=broker_id)

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.delete(f"/symbols/{symbol_id1}")
            assert response.status_code == 200
            try:
                res = await read_symbol(conn, id=symbol_id1)
            except Exception as ex:
                assert isinstance(ex, NotFoundError)

            # try to del unknown symbol
            response = await ac.delete(f"/symbols/{999}")
            assert response.status_code == 404

            res = await read_symbol(conn, id=symbol_id2)
            assert res['name'] == 'ETHUSDT'