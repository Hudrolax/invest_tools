import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import UserORM
from models.currency import CurrencyORM
from models.symbol import SymbolORM


@pytest.mark.asyncio
async def test_create_currency(client: AsyncClient, db_session: AsyncSession, jwt_token: tuple[str, UserORM]):
    payload = dict(
        name = 'RUB'
    )
    response = await client.post(f"/currencies/", json=payload)
    assert response.status_code == 401

    token, user = jwt_token
    headers = dict(TOKEN=token)
    response = await client.post(f"/currencies/", headers=headers, json=payload)
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result['id'], int)
    assert result['name'] == payload['name']

    symbols = await SymbolORM.get_list(db_session)
    assert len(symbols) == 5


@pytest.mark.asyncio
async def test_read_currency(client: AsyncClient, db_session: AsyncSession, jwt_token: tuple[str, UserORM]):
    response = await client.get(f"/currencies/999")
    assert response.status_code == 401

    payload = dict(
        name = 'RUB'
    )

    currency = await CurrencyORM.create(db_session, **payload)

    token, user = jwt_token
    headers = dict(TOKEN=token)
    response = await client.get(f"/currencies/999", headers=headers)
    assert response.status_code == 404

    response = await client.get(f"/currencies/{currency.id}", headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert result['name'] == payload['name']


@pytest.mark.asyncio
async def test_read_currencies(client: AsyncClient, db_session: AsyncSession, jwt_token: tuple[str, UserORM]):
    response = await client.get(f"/currencies/")
    assert response.status_code == 401

    token, user = jwt_token
    headers = dict(TOKEN=token)
    response = await client.get(f"/currencies/", headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert len(result) == 0

    currency1 = await CurrencyORM.create(db_session, name='RUB')
    currency2 = await CurrencyORM.create(db_session, name='ARS')
    response = await client.get(f"/currencies/", headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]['name'] == currency1.name
    assert result[1]['name'] == currency2.name


@pytest.mark.asyncio
async def test_update_currency(client: AsyncClient, db_session: AsyncSession, jwt_token: tuple[str, UserORM]):
    payload = dict(
        name = 'RUB'
    )

    response = await client.put(f"/currencies/999", json=payload)
    assert response.status_code == 401

    currency = await CurrencyORM.create(db_session, name='ARS')

    token, user = jwt_token
    headers = dict(TOKEN=token)

    response = await client.put(f"/currencies/999", headers=headers, json=payload)
    assert response.status_code == 404

    response = await client.put(f"/currencies/{currency.id}", headers=headers, json=payload)
    assert response.status_code == 200
    assert response.json()['name'] == payload['name']


@pytest.mark.asyncio
async def test_delete_currency(client: AsyncClient, db_session: AsyncSession, jwt_token: tuple[str, UserORM]):
    response = await client.delete(f"/currencies/999")
    assert response.status_code == 401

    token, user = jwt_token
    headers = dict(TOKEN=token)
    response = await client.delete(f"/currencies/999", headers=headers)
    assert response.status_code == 404

    currency = await CurrencyORM.create(db_session, name='RUB')
    response = await client.delete(f"/currencies/{currency.id}", headers=headers)
    assert response.status_code == 200
    assert response.json() == True
