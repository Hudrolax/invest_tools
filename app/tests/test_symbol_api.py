import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from models.symbol import SymbolORM
from models.broker import BrokerORM


@pytest.mark.asyncio
async def test_read_symbols(client: AsyncClient, db_session: AsyncSession, token: str):
    broker = (await BrokerORM.get_all(db_session))[0]

    # test reading empty symbol list
    headers = dict(TOKEN=token)
    response = await client.get(f"/symbols/", headers=headers)
    assert response.status_code == 200
    assert response.json() == []

    # add symbols
    payload1 = dict(
        name='BTCUSDT',
        broker_id=broker.id,
        rate=Decimal('12.75')
    )
    payload2 = dict(
        name='ETHUSDT',
        broker_id=broker.id,
        rate=Decimal('12.75')
    )
    await SymbolORM.create(db_session, **payload1)
    await SymbolORM.create(db_session, **payload2)

    response = await client.get(f"/symbols/", headers=headers)
    assert response.status_code == 200
    result = response.json() 
    for key in payload1.keys():
        if key == 'rate':
            assert Decimal(result[0][key]) == payload1[key]
        else:
            assert result[0][key] == payload1[key]
    for key in payload2.keys():
        if key == 'rate':
            assert Decimal(result[1][key]) == payload2[key]
        else:
            assert result[1][key] == payload2[key]


@pytest.mark.asyncio
async def test_read_symbols2(client: AsyncClient, db_session: AsyncSession, token: str, symbols):
    headers = dict(TOKEN=token)
    params = dict(
        symbol_names = ['BTCUSDT'],
        broker_name = 'Binance-spot',
    )
    response = await client.get(f"/symbols/", headers=headers, params=params)
    assert response.status_code == 200
    result = response.json()
    assert result[0]['name'] == 'BTCUSDT'