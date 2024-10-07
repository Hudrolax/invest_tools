import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import TELEGRAM_BOT_SECRET, OPENAI_API_KEY
from models.user import UserORM
from .conftest import make_user


@pytest.mark.asyncio
async def test_create_user(client: AsyncClient):
    payload = dict(
        username='New user',
        password='123',
        telegram_id=123,
        email='user@example.com',
        name='John Doe'
    )
    response = await client.post("/users/register", json=payload)
    assert response.status_code == 200
    result = response.json()
    assert result['username'] == payload['username']
    assert result['telegram_id'] == payload['telegram_id']
    assert result['email'] == payload['email']
    assert result['name'] == payload['name']

    # another one user with same name
    payload = dict(
        username='New user',
        password='123',
        telegram_id=1234,
        email='user2@example.com'
    )
    response = await client.post("/users/register", json=payload)
    assert response.status_code == 422

    # another one user without name
    payload = dict(
        telegram_id=12345,
        password='123',
        email='user3@example.com'
    )
    response = await client.post("/users/register", json=payload)
    assert response.status_code == 422


    # another one user without password
    payload = dict(
        username='New user',
        telegram_id=12345,
        email='user3@example.com'
    )
    response = await client.post("/users/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_user_wrong(client: AsyncClient, db_session: AsyncSession):
    # user without telegram_id and email
    payload = dict(
        username='empty user'
    )
    response = await client.post("/users/register", json=payload)
    assert response.status_code == 422

    # user with only telegram_id
    payload = dict(
        username='empty user',
        password='123',
        telegram_id=123456,
        name='John Doe'
    )
    response = await client.post("/users/register", json=payload)
    assert response.status_code == 200

    # user with only email
    payload = dict(
        username='empty user2',
        password='123',
        email='onlyemail@example.com',
        name='John Doe'
    )
    response = await client.post("/users/register", json=payload)
    assert response.status_code == 200

    # with same email
    payload['email'] = 'user@example.com'
    payload['username'] = 'user3'
    await UserORM.create(db_session, **payload)

    response = await client.post("/users/register", json=payload)
    assert response.status_code == 422

    # with same telegram id
    payload['username'] = 'user4'
    await UserORM.create(db_session, **payload)

    response = await client.post("/users/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_read_user(client: AsyncClient, db_session: AsyncSession):
    # try to read unauthorized user
    response = await client.get(f"/users/{999}")
    assert response.status_code == 401

    payload = dict(
        username='New user',
        password='123',
        telegram_id=123,
        email='user@example.com'
    )
    user, token = await make_user(db_session, **payload)  # type: ignore
    response = await client.get(f"/users/{user.id}", headers=dict(TOKEN='123'))
    assert response.status_code == 200
    result = response.json()
    assert result['username'] == payload['username']
    assert result['telegram_id'] == payload['telegram_id']
    assert result['email'] == payload['email']


@pytest.mark.asyncio
async def test_read_user_telegram_bot_api(client: AsyncClient, db_session: AsyncSession):
    # try to read unauthorized user
    response = await client.get(f"/users/{999}")
    assert response.status_code == 401

    payload = dict(
        username='New user',
        password='123',
        telegram_id=123,
        email='user@example.com'
    )
    user, _ = await make_user(db_session, **payload)  # type: ignore
    headers: dict[str, str] = {'TBOT-SECRET': TELEGRAM_BOT_SECRET} # type: ignore
    response = await client.get(f"/users/telegram_bot_api/{user.id}", headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert result['username'] == payload['username']
    assert result['telegram_id'] == payload['telegram_id']
    assert result['email'] == payload['email']

@pytest.mark.asyncio
async def test_read_users(client: AsyncClient, db_session: AsyncSession):
    superuser, token = await make_user(db_session, username='super', telegram_id=999)
    superuser.superuser = True  # type: ignore
    await db_session.flush()
    await db_session.refresh(superuser)
    headers = dict(TOKEN=token.token)

    # try to get empty user list
    response = await client.get(f"/users/", headers=headers)  # type: ignore
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]['id'] == superuser.id

    payload1 = dict(
        username='New user',
        password='123',
        telegram_id=123,
        email='user2@example.com'
    )
    payload2 = dict(
        username='New user2',
        password='123',
        telegram_id=1234,
        email='user3@example.com'
    )
    await UserORM.create(db_session, **payload1)
    await UserORM.create(db_session, **payload2)
    response = await client.get(f"/users/", headers=headers)  # type: ignore
    assert response.status_code == 200
    result = response.json()
    assert len(result) == 3
    assert result[1]['username'] == payload1['username']
    assert result[1]['telegram_id'] == payload1['telegram_id']
    assert result[1]['email'] == payload1['email']
    assert result[2]['username'] == payload2['username']
    assert result[2]['telegram_id'] == payload2['telegram_id']
    assert result[2]['email'] == payload2['email']


@pytest.mark.asyncio
async def test_update_user(client: AsyncClient, db_session: AsyncSession):
    # test update unexisting user
    response = await client.put(f"/users/{999}", json=dict(telegram_id=999))
    assert response.status_code == 401

    payload = dict(
        username='New user',
        password='123',
        telegram_id=123,
        email='user@example.com'
    )
    user, token = await make_user(db_session, **payload)  # type: ignore

    headers = dict(TOKEN=token.token)
    response = await client.put(f"/users/{user.id}", headers=headers, json=dict(telegram_id=999)) # type: ignore
    assert response.status_code == 200
    result = response.json()
    assert result['telegram_id'] == 999


@pytest.mark.asyncio
async def test_update_user_double_email(client: AsyncClient, db_session: AsyncSession):
    payload1 = dict(
        username='New user',
        password='123',
        telegram_id=123,
        email='user@example.com'
    )
    payload2 = dict(
        username='New user2',
        password='123',
        telegram_id=1234,
        email='user2@example.com'
    )
    user, token = await make_user(db_session, **payload1) # type: ignore
    await UserORM.create(db_session, **payload2)

    headers = dict(TOKEN=token.token)
    response = await client.put(f"/users/{user.id}", headers=headers, json=dict(telegram_id=payload2['email'])) # type: ignore
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_user_double_telegram_id(client: AsyncClient, db_session: AsyncSession):
    payload1 = dict(
        username='New user',
        password='123',
        telegram_id=123,
        email='user@example.com'
    )
    payload2 = dict(
        username='New user2',
        password='123',
        telegram_id=1234,
        email='user2@example.com'
    )
    user, token = await make_user(db_session, **payload1) # type: ignore
    await UserORM.create(db_session, **payload2)

    headers = dict(TOKEN=token.token)
    response = await client.put(f"/users/{user.id}", headers=headers, json=dict(telegram_id=payload2['telegram_id'])) # type: ignore
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login(client: AsyncClient, db_session: AsyncSession):
    payload1 = dict(
        username='New user',
        password='123',
        telegram_id=123,
        email='user@example.com'
    )
    user, _ = await make_user(db_session, **payload1)  # type: ignore

    payload = dict(
            username='New user',
            password='123'
        )

    response = await client.post("/users/login", json=payload)
    assert response.status_code == 200
    result = response.json()
    assert result['user_id'] == user.id
    assert result['openai_api_key'] == OPENAI_API_KEY


# @pytest.mark.asyncio
# async def test_get_openai_api_key(client: AsyncClient, db_session: AsyncSession):
#     payload = dict(
#         username='New user',
#         password='123',
#         telegram_id=123,
#         email='user@example.com'
#     )
#     user, token = await make_user(db_session, **payload)  # type: ignore
#     response = await client.get(f"/users/{user.id}/openai_key", headers=dict(TOKEN='123'))
#     assert response.status_code == 200
#     result = response.json()
#     assert result['key'] == OPENAI_API_KEY
