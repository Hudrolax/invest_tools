import pytest
from httpx import AsyncClient
from main import app
from db.db_connection import db
from tests.unit.fixtures import db_setup
from models.users import read_user, read_users, add_user


@pytest.mark.asyncio
async def test_add_user(db_setup):
    async for conn in db_setup:
        app.dependency_overrides[db.get_conn] = lambda: conn

        async with AsyncClient(app=app, base_url="http://test") as ac:
            payload = dict(
                name='test_user',
                telegram_id=123456789,
                email='user@example.com',
            )

            response = await ac.post("/users/", json=payload)

            assert response.status_code == 200

            data = response.json()
            assert data['name'] == payload['name']
            assert data['telegram_id'] == payload['telegram_id']
            assert data['email'] == payload['email']
            assert isinstance(data['id'], int)

            data = await read_user(conn, user_id=data['id'])
            assert data['name'] == payload['name']
            assert data['telegram_id'] == payload['telegram_id']

            # test adding a user with wrong email
            payload = dict(
                name='test_user',
                email='dj4jn.d'
            )
            response = await ac.post("/users/", json=payload)
            assert response.status_code == 422


@pytest.mark.asyncio
async def test_read_user(db_setup):
    async for conn in db_setup:
        app.dependency_overrides[db.get_conn] = lambda: conn

        async with AsyncClient(app=app, base_url="http://test") as ac:
            user_id = await add_user(conn, name='user1', telegram_id=123)

            response = await ac.get(f"/users/{user_id}")
            assert response.status_code == 200
            data = response.json()
            assert data['name'] == 'user1'
            assert data['telegram_id'] == 123
            assert data['email'] == None
            assert isinstance(data['id'], int)

            # read unknown user
            response = await ac.get(f"/users/{999}")
            print(response.text)
            assert response.status_code == 404

@pytest.mark.asyncio
async def test_read_users(db_setup):
    async for conn in db_setup:
        app.dependency_overrides[db.get_conn] = lambda: conn

        async with AsyncClient(app=app, base_url="http://test") as ac:
            user_id1 = await add_user(conn, name='user1', telegram_id=123)
            user_id2 = await add_user(conn, name='user2', telegram_id=1234)

            response = await ac.get(f"/users/")
            assert response.status_code == 200
            data = response.json()['users']
            assert len(data) == 2
            assert data[0]['id'] == user_id1
            assert data[1]['id'] == user_id2


@pytest.mark.asyncio
async def test_update_user(db_setup):
    async for conn in db_setup:
        app.dependency_overrides[db.get_conn] = lambda: conn

        user_id = await add_user(conn, name='user1', telegram_id=123)

        async with AsyncClient(app=app, base_url="http://test") as ac:
            payload = dict(
                name='test_user',
                telegram_id=123456789,
                email='test@example.com'
            )

            response = await ac.put(f"/users/{user_id}", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data['name'] == payload['name']
            assert data['telegram_id'] == payload['telegram_id']
            assert data['email'] == payload['email']

            data = await read_user(conn, user_id=user_id)
            assert data['name'] == payload['name']
            assert data['telegram_id'] == payload['telegram_id']
            assert data['email'] == payload['email']
            
            