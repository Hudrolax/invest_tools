import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import UserORM
from models.exin_item import ExInItemORM
from models.user_exin_items import UserExInItemORM


@pytest.mark.asyncio
async def test_create_exin_item(client: AsyncClient, db_session: AsyncSession, jwt_token: tuple[str, UserORM]):
    payload = dict(
        name = 'Продукты',
        income = False
    )
    response = await client.post(f"/exin_items/", json=payload)
    assert response.status_code == 401

    token, user = jwt_token
    headers = dict(TOKEN=token)
    response = await client.post(f"/exin_items/", headers=headers, json=payload)
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result['id'], int)
    assert result['name'] == payload['name']

    user_exin_items = await UserExInItemORM.get_list(db_session, user_id=user.id)
    assert len(user_exin_items) == 1
    assert user_exin_items[0].user_id == user.id # type: ignore
    assert user_exin_items[0].exin_item_id == result['id']


@pytest.mark.asyncio
async def test_read_exin_item(client: AsyncClient, db_session: AsyncSession, jwt_token: tuple[str, UserORM]):
    response = await client.get(f"/exin_items/999")
    assert response.status_code == 401

    payload = dict(
        name = 'Продукты'
    )

    token, user = jwt_token
    exin_item = await ExInItemORM.create(db_session, user_id=user.id, **payload)

    headers = dict(TOKEN=token)
    response = await client.get(f"/exin_items/999", headers=headers)
    assert response.status_code == 404

    response = await client.get(f"/exin_items/{exin_item.id}", headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert result['name'] == payload['name']


@pytest.mark.asyncio
async def test_read_exin_items(client: AsyncClient, db_session: AsyncSession, jwt_token: tuple[str, UserORM]):
    response = await client.get(f"/exin_items/")
    assert response.status_code == 401

    token, user = jwt_token
    headers = dict(TOKEN=token)
    response = await client.get(f"/exin_items/", headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert len(result) == 0

    exin_item1 = await ExInItemORM.create(db_session, user_id=user.id, name='Продукты')
    exin_item2 = await ExInItemORM.create(db_session, user_id=user.id, name='Здоровье')
    response = await client.get(f"/exin_items/", headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]['name'] == exin_item1.name
    assert result[1]['name'] == exin_item2.name


@pytest.mark.asyncio
async def test_update_exin_item(client: AsyncClient, db_session: AsyncSession, jwt_token: tuple[str, UserORM]):
    payload = dict(
        name = 'Здоровье',
        income = False
    )

    response = await client.put(f"/exin_items/999", json=payload)
    assert response.status_code == 401

    token, user = jwt_token
    exin_item = await ExInItemORM.create(db_session, user_id=user.id, name='Продукты')

    headers = dict(TOKEN=token)

    response = await client.put(f"/exin_items/999", headers=headers, json=payload)
    assert response.status_code == 404

    response = await client.put(f"/exin_items/{exin_item.id}", headers=headers, json=payload)
    assert response.status_code == 200
    assert response.json()['name'] == payload['name']


@pytest.mark.asyncio
async def test_delete_exin_item(client: AsyncClient, db_session: AsyncSession, jwt_token: tuple[str, UserORM]):
    response = await client.delete(f"/exin_items/999")
    assert response.status_code == 401

    token, user = jwt_token
    headers = dict(TOKEN=token)
    response = await client.delete(f"/exin_items/999", headers=headers)
    assert response.status_code == 404

    exin_item = await ExInItemORM.create(db_session, user_id=user.id, name='Продукты')
    response = await client.delete(f"/exin_items/{exin_item.id}", headers=headers)
    assert response.status_code == 200
    assert response.json() == True

    user_exin_items = await UserExInItemORM.get_list(db_session, user_id=user.id)
    assert len(user_exin_items) == 0