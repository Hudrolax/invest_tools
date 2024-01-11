import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from decimal import Decimal

from models.user import UserORM
from models.currency import CurrencyORM
from models.wallet import WalletORM
from models.exin_item import ExInItemORM
from models.wallet_transaction import WalletTransactionORM


@pytest.mark.asyncio
async def test_create_wallet_transaction_unauthorized(client: AsyncClient, db_session: AsyncSession, jwt_token: tuple[str, UserORM]):
    # unauthorized
    response = await client.post(f"/wallet_transactions/", json={})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_wallet_transaction_wrong_payload(client: AsyncClient, db_session: AsyncSession, jwt_token: tuple[str, UserORM]):
    token, user = jwt_token
    headers = dict(TOKEN=token)
    response = await client.post(f"/wallet_transactions/", headers=headers, json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_wallet_transaction_regular(
    client: AsyncClient,
    db_session: AsyncSession,
    jwt_token: tuple[str, UserORM],
    symbols
) -> None:
    token, user = jwt_token
    currency = await CurrencyORM.create(db_session, name='ARS')
    wallet = await WalletORM.create(db_session, user_id=user.id, name='Нал ARS', currency_id=currency.id)
    exin_item = await ExInItemORM.create(db_session, user_id=user.id, name='Продукты')

    payload = dict(
        wallet_from_id=wallet.id,
        exin_item_id=exin_item.id,
        amount='-12345',
        comment='Carrefour',
    )
    headers = dict(TOKEN=token)
    response = await client.post(f"/wallet_transactions/", headers=headers, json=payload)
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert len(result) == 1
    result = result[0]

    assert result['wallet_id'] == payload['wallet_from_id']
    assert result['exin_item_id'] == payload['exin_item_id']
    assert result['amount'] == payload['amount']
    assert result['amountARS'] == payload['amount']
    assert result['amountUSD'] == '-12.59'
    assert result['amountBTC'] == '-0.00030454'
    assert result['amountETH'] == '-0.00609088'
    assert result['amountRUB'] == '-1194.14'
    assert result['comment'] == payload['comment']
    assert result['doc_id']
    assert result['user_id'] == user.id
    assert result['user_name'] == user.name
    assert isinstance(datetime.fromisoformat(result['date']), datetime)

    # check wallet balance
    await db_session.refresh(wallet)
    assert wallet.balance == Decimal(payload['amount'])  # type: ignore


@pytest.mark.asyncio
async def test_create_wallet_transaction_exchange(
    client: AsyncClient,
    db_session: AsyncSession,
    jwt_token: tuple[str, UserORM],
    symbols,
) -> None:
    token, user = jwt_token
    currency1 = await CurrencyORM.create(db_session, name='ARS')
    wallet1 = await WalletORM.create(db_session, user_id=user.id, name='Нал ARS', currency_id=currency1.id)
    currency2 = await CurrencyORM.create(db_session, name='USD')
    wallet2 = await WalletORM.create(db_session, user_id=user.id, name='Нал USD', currency_id=currency2.id)

    payload = dict(
        wallet_from_id=wallet2.id,
        wallet_to_id=wallet1.id,
        amount='300',
        exchange_rate='960',
        comment='Florida 656',
    )
    headers = dict(TOKEN=token)
    response = await client.post(f"/wallet_transactions/", headers=headers, json=payload)
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]['wallet_id'] == payload['wallet_from_id']
    assert result[0]['amount'] == f"-{payload['amount']}"
    assert result[0]['comment'] == payload['comment']

    assert result[1]['wallet_id'] == payload['wallet_to_id']
    assert result[1]['amount'] == '288000'
    assert result[1]['comment'] == payload['comment']

    assert result[0]['doc_id'] == result[1]['doc_id']
    assert result[0]['date'] == result[1]['date']

    # check wallet balance
    await db_session.refresh(wallet1)
    await db_session.refresh(wallet2)
    assert wallet2.balance == Decimal(f'-{payload['amount']}')  # type: ignore
    assert wallet1.balance == Decimal('288000') # type: ignore

@pytest.mark.asyncio
async def test_update_wallet_transaction_unauthorized(client: AsyncClient, db_session: AsyncSession, jwt_token: tuple[str, UserORM]):
    response = await client.put(f"/wallet_transactions/999", json={})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_wallet_transaction_wrong_data(
    client: AsyncClient,
    db_session: AsyncSession,
    jwt_token: tuple[str, UserORM],
):
    token, user = jwt_token
    headers = dict(TOKEN=token)

    response = await client.put(f"/wallet_transactions/999", headers=headers, json={})
    assert response.status_code == 422

    payload = dict(
        wallet_from_id=1,
        wallet_to_id=None,
        exin_item_id=1,
        amount='-333',
        exchange_rate=None,
        date=datetime.now().isoformat(),
        comment='Carrefour2',
    )
    response = await client.put(f"/wallet_transactions/999", headers=headers, json=payload)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_wallet_transaction_regular(
    client: AsyncClient,
    db_session: AsyncSession,
    jwt_token: tuple[str, UserORM],
    symbols,
):
    token, user = jwt_token
    currency = await CurrencyORM.create(db_session, name='ARS')
    wallet = await WalletORM.create(db_session, user_id=user.id, name='Нал ARS', currency_id=currency.id)
    exin_item = await ExInItemORM.create(db_session, user_id=user.id, name='Продукты')
    payload = dict(
        wallet_id=wallet.id,
        exin_item_id=exin_item.id,
        amount='-12345',
        comment='Carrefour',
        user_id=user.id,
    )
    trz = await WalletTransactionORM.create(db_session, **payload)
    await db_session.refresh(wallet)
    assert wallet.balance == Decimal(payload['amount'])  # type: ignore

    headers = dict(TOKEN=token)
    payload = dict(
        wallet_from_id=wallet.id,
        wallet_to_id=None,
        exin_item_id=exin_item.id,
        amount='-333',
        exchange_rate=None,
        date=trz.date.isoformat(),
        comment='Carrefour2',
    )
    response = await client.put(f"/wallet_transactions/{trz.doc_id}", headers=headers, json=payload)
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]['amount'] == payload['amount']
    assert result[0]['comment'] == payload['comment']
    assert result[0]['doc_id'] == trz.doc_id
    assert datetime.fromisoformat(result[0]['date']) == trz.date

    # check wallet balance
    await db_session.refresh(wallet)
    assert wallet.balance == Decimal(payload['amount'])  # type: ignore


@pytest.mark.asyncio
async def test_update_wallet_transaction_exchange(
    client: AsyncClient,
    db_session: AsyncSession,
    jwt_token: tuple[str, UserORM],
    symbols,
):
    token, user = jwt_token
    currency1 = await CurrencyORM.create(db_session, name='ARS')
    wallet1 = await WalletORM.create(db_session, user_id=user.id, name='Нал ARS', currency_id=currency1.id)
    currency2 = await CurrencyORM.create(db_session, name='USD')
    wallet2 = await WalletORM.create(db_session, user_id=user.id, name='Нал USD', currency_id=currency2.id)
    payload = dict(
        wallet_id=wallet2.id,
        amount='-300',
        user_id=user.id,
        doc_id='xxx'
    )
    trz1 = await WalletTransactionORM.create(db_session, **payload)
    payload = dict(
        wallet_id=wallet1.id,
        amount='282000',
        user_id=user.id,
        doc_id='xxx'
    )
    trz2 = await WalletTransactionORM.create(db_session, **payload)

    headers = dict(TOKEN=token)
    payload = dict(
        wallet_from_id=wallet2.id,
        wallet_to_id=wallet1.id,
        exin_item_id=None,
        amount='200',
        exchange_rate='950',
    )
    response = await client.put(f"/wallet_transactions/{trz1.doc_id}", headers=headers, json=payload)
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]['wallet_id'] == wallet2.id
    assert result[1]['wallet_id'] == wallet1.id
    assert result[0]['amount'] == f'-{payload['amount']}'
    assert Decimal(result[1]['amount']) == Decimal(
        payload['amount']) * Decimal(payload['exchange_rate'])  # type: ignore

    # check wallet balance
    await db_session.refresh(wallet1)
    await db_session.refresh(wallet2)
    assert wallet1.balance == Decimal(
        payload['amount']) * Decimal(payload['exchange_rate'])  # type: ignore
    assert wallet2.balance == -Decimal(payload['amount'])  # type: ignore


@pytest.mark.asyncio
async def test_get_wallet_transaction_by_doc_id_unauthorized(
    client: AsyncClient,
    db_session: AsyncSession,
    jwt_token: tuple[str, UserORM],
    symbols,
):
    response = await client.get(f"/wallet_transactions/999")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_wallet_transaction_by_doc_id_404(
    client: AsyncClient,
    db_session: AsyncSession,
    jwt_token: tuple[str, UserORM],
):
    token, user = jwt_token
    headers = dict(TOKEN=token)
    response = await client.get(f"/wallet_transactions/999", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_wallet_transaction_by_doc_id(
    client: AsyncClient,
    db_session: AsyncSession,
    jwt_token: tuple[str, UserORM],
    symbols,
):
    token, user = jwt_token
    exin_item = await ExInItemORM.create(db_session, user_id=user.id, name='Продукты')
    currency = await CurrencyORM.create(db_session, name='ARS')
    wallet = await WalletORM.create(db_session, user_id=user.id, name='Нал ARS', currency_id=currency.id)
    payload = dict(
        wallet_id=wallet.id,
        exin_item_id=exin_item.id,
        amount='-3000',
        user_id=user.id,
    )
    trz = await WalletTransactionORM.create(db_session, **payload)

    token, user = jwt_token
    headers = dict(TOKEN=token)
    response = await client.get(f"/wallet_transactions/{trz.doc_id}", headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]['wallet_id'] == payload['wallet_id']
    assert result[0]['exin_item_id'] == payload['exin_item_id']
    assert result[0]['amount'] == payload['amount']
    assert result[0]['user_id'] == payload['user_id']
    assert result[0]['doc_id'] == trz.doc_id
    assert result[0]['id'] == trz.id


@pytest.mark.asyncio
async def test_get_wallet_transaction_list(
    client: AsyncClient,
    db_session: AsyncSession,
    jwt_token: tuple[str, UserORM],
    symbols
):
    token, user = jwt_token
    exin_item = await ExInItemORM.create(db_session, user_id=user.id, name='Продукты')
    currency = await CurrencyORM.create(db_session, name='ARS')
    wallet = await WalletORM.create(db_session, user_id=user.id, name='Нал ARS', currency_id=currency.id)
    payload = dict(
        wallet_id=wallet.id,
        exin_item_id=exin_item.id,
        amount='-3000',
        user_id=user.id,
    )
    trz1 = await WalletTransactionORM.create(db_session, **payload)
    trz2 = await WalletTransactionORM.create(db_session, **payload)
    trz3 = await WalletTransactionORM.create(db_session, comment='xxx', **payload)

    token, user = jwt_token
    headers = dict(TOKEN=token)
    response = await client.get(f"/wallet_transactions/", headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert len(result) == 3
    assert result[0]['wallet_id'] == payload['wallet_id']
    assert result[0]['exin_item_id'] == payload['exin_item_id']
    assert result[0]['amount'] == payload['amount']
    assert result[0]['user_id'] == payload['user_id']
    assert result[0]['doc_id'] == trz1.doc_id
    assert result[0]['id'] == trz1.id
    assert result[0]['user_name'] == user.name
    assert result[1]['doc_id'] == trz2.doc_id
    assert result[1]['id'] == trz2.id
    assert result[1]['user_name'] == user.name
    assert result[2]['doc_id'] == trz3.doc_id
    assert result[2]['id'] == trz3.id
    assert result[2]['user_name'] == user.name

    response = await client.get(f"/wallet_transactions/", headers=headers, params=dict(comment='xxx'))
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]['doc_id'] == trz3.doc_id


@pytest.mark.asyncio
async def test_del_wallet_transaction_unauthorized(client: AsyncClient, db_session: AsyncSession, jwt_token: tuple[str, UserORM]):
    response = await client.delete(f"/wallet_transactions/999")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_del_wallet_transaction_404(client: AsyncClient, db_session: AsyncSession, jwt_token: tuple[str, UserORM]):
    token, user = jwt_token
    headers = dict(TOKEN=token)
    response = await client.delete(f"/wallet_transactions/999", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_del_wallet_transaction(
    client: AsyncClient,
    db_session: AsyncSession,
    jwt_token: tuple[str, UserORM],
    symbols,
):
    token, user = jwt_token
    exin_item = await ExInItemORM.create(db_session, user_id=user.id, name='Продукты')
    currency = await CurrencyORM.create(db_session, name='ARS')
    wallet = await WalletORM.create(db_session, user_id=user.id, name='Нал ARS', currency_id=currency.id)
    payload = dict(
        wallet_id=wallet.id,
        exin_item_id=exin_item.id,
        amount='-3000',
        user_id=user.id,
    )

    trz = await WalletTransactionORM.create(db_session, **payload)
    token, user = jwt_token
    headers = dict(TOKEN=token)
    response = await client.delete(f"/wallet_transactions/{trz.doc_id}", headers=headers)
    assert response.status_code == 200
    assert response.json() == True

    await db_session.refresh(wallet)
    assert wallet.balance == 0  # type: ignore
