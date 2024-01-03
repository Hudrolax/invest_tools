import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from models.user import UserORM
from models.currency import CurrencyORM
from models.wallet import WalletORM
from models.user_wallets import UserWalletsORM


@pytest.mark.asyncio
async def test_create_wallet(client: AsyncClient, db_session: AsyncSession, jwt_token: tuple[str, UserORM]):
    # unauthorized
    response = await client.post(f"/wallets/", json={})
    assert response.status_code == 401

    # authorized
    currency = await CurrencyORM.create(db_session, name='ARS')
    payload = dict(
        name = 'Нал ARS',
        currency_id = currency.id,
    )
    token, user = jwt_token
    headers = dict(TOKEN=token)
    response = await client.post(f"/wallets/", headers=headers, json=payload)
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result['id'], int)
    assert result['name'] == payload['name']
    assert result['currency_id'] == payload['currency_id']
    assert Decimal(result['balance']) == Decimal(0)

    user_wallets = await UserWalletsORM.get_list(db_session, user_id=user.id)
    assert len(user_wallets) == 1
    assert user_wallets[0].user_id == user.id # type: ignore
    assert user_wallets[0].wallet_id == result['id'] # type: ignore


@pytest.mark.asyncio
async def test_read_wallet(client: AsyncClient, db_session: AsyncSession, jwt_token: tuple[str, UserORM]):
    # unauthorized
    response = await client.get(f"/wallets/999")
    assert response.status_code == 401

    # 404
    token, user = jwt_token
    headers = dict(TOKEN=token)
    response = await client.get(f"/wallets/999", headers=headers)
    assert response.status_code == 404

    # authorized
    currency = await CurrencyORM.create(db_session, name='ARS')
    payload = dict(
        name = 'Нал ARS',
        currency_id = currency.id,
        balance = Decimal('35.99')
    )
    wallet = await WalletORM.create(db_session, user_id=user.id, **payload)

    response = await client.get(f"/wallets/{wallet.id}", headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert result['name'] == payload['name']
    assert result['currency_id'] == payload['currency_id']
    assert Decimal(result['balance']) == payload['balance']


@pytest.mark.asyncio
async def test_read_wallets(client: AsyncClient, db_session: AsyncSession, jwt_token: tuple[str, UserORM]):
    # unauthorized
    response = await client.get(f"/wallets/")
    assert response.status_code == 401

    # empty
    token, user = jwt_token
    headers = dict(TOKEN=token)
    response = await client.get(f"/wallets/", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 0

    # authorized
    currency1 = await CurrencyORM.create(db_session, name='ARS')
    currency2 = await CurrencyORM.create(db_session, name='USD')
    payload1 = dict(
        name = 'Нал ARS',
        currency_id = currency1.id,
    )
    payload2 = dict(
        name = 'Нал USD',
        currency_id = currency2.id,
    )
    wallet1 = await WalletORM.create(db_session, user_id=user.id, **payload1)
    wallet2 = await WalletORM.create(db_session, user_id=user.id, **payload2)

    response = await client.get(f"/wallets/", headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]['name'] == payload1['name']
    assert result[0]['currency_id'] == payload1['currency_id']
    assert result[1]['name'] == payload2['name']
    assert result[1]['currency_id'] == payload2['currency_id']


@pytest.mark.asyncio
async def test_update_wallet(client: AsyncClient, db_session: AsyncSession, jwt_token: tuple[str, UserORM]):
    # unauthorized
    response = await client.put(f"/wallets/999", json={})
    assert response.status_code == 401

    # 404
    token, user = jwt_token
    headers = dict(TOKEN=token)
    response = await client.put(f"/wallets/999", headers=headers, json={})
    assert response.status_code == 404

    # authorized
    currency = await CurrencyORM.create(db_session, name='ARS')
    payload = dict(
        name = 'Нал ARS',
        currency_id = currency.id,
        balance = Decimal('30.99')
    )
    wallet = await WalletORM.create(db_session, user_id=user.id,**payload)

    payload_new = dict(
        balance = '29.88'
    )
    response = await client.put(f"/wallets/{wallet.id}", headers=headers, json=payload_new)
    assert response.status_code == 200
    result = response.json()
    assert result['name'] == payload['name']
    assert result['currency_id'] == payload['currency_id']
    assert Decimal(result['balance']) == Decimal(payload_new['balance'])


@pytest.mark.asyncio
async def test_delete_wallet(client: AsyncClient, db_session: AsyncSession, jwt_token: tuple[str, UserORM]):
    # unauthorized
    response = await client.delete(f"/wallets/999")
    assert response.status_code == 401

    # 404
    token, user = jwt_token
    headers = dict(TOKEN=token)
    response = await client.delete(f"/wallets/999", headers=headers)
    assert response.status_code == 404

    # authorized
    currency = await CurrencyORM.create(db_session, name='ARS')
    payload = dict(
        name = 'Нал ARS',
        currency_id = currency.id,
    )
    wallet = await WalletORM.create(db_session, user_id=user.id, **payload)

    response = await client.delete(f"/wallets/{wallet.id}", headers=headers)
    assert response.status_code == 200
    assert response.json() == True

    user_wallets = await UserWalletsORM.get_list(db_session, user_id=user.id)
    assert len(user_wallets) == 0