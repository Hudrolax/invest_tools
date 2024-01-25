import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import UserORM
from models.checklist import ChecklistORM
from datetime import datetime


@pytest.mark.asyncio
async def test_create_cheklist_item(client: AsyncClient, db_session: AsyncSession, jwt_token: tuple[str, UserORM]):
    payload = dict(
        text = 'Хлеб'
    )
    response = await client.post(f"/checklist/", json=payload)
    assert response.status_code == 401

    token, user = jwt_token
    headers = dict(TOKEN=token)
    response = await client.post(f"/checklist/", headers=headers, json=payload)
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result['id'], int)
    assert result['text'] == payload['text']
    assert result['user_id'] == user.id
    assert result['checked'] == False
    assert isinstance(datetime.fromisoformat(result['date']), datetime)

    checklist = await ChecklistORM.get_list(db_session)
    assert len(checklist) == 1
    assert checklist[0].id == result['id']

@pytest.mark.asyncio
async def test_read_checklist(client: AsyncClient, db_session: AsyncSession, jwt_token: tuple[str, UserORM]):
    response = await client.get(f"/checklist/")
    assert response.status_code == 401

    token, user = jwt_token
    headers = dict(TOKEN=token)
    response = await client.get(f"/checklist/", headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert len(result) == 0

    checklist_item1 = await ChecklistORM.create(db_session, text='Хлеб', user_id=user.id)
    checklist_item2 = await ChecklistORM.create(db_session, text='Молоко', user_id=user.id)
    response = await client.get(f"/checklist/", headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]['text'] == checklist_item1.text
    assert result[1]['text'] == checklist_item2.text


@pytest.mark.asyncio
async def test_update_checklist(client: AsyncClient, db_session: AsyncSession, jwt_token: tuple[str, UserORM]):
    payload = dict(
        checked = True
    )

    response = await client.put(f"/checklist/999", json=payload)
    assert response.status_code == 401

    token, user = jwt_token
    headers = dict(TOKEN=token)

    response = await client.put(f"/checklist/999", headers=headers, json=payload)
    assert response.status_code == 404

    checklist_item = await ChecklistORM.create(db_session, text='Хлеб', user_id=user.id)
    response = await client.put(f"/checklist/{checklist_item.id}", headers=headers, json=payload)
    assert response.status_code == 200
    assert response.json()['checked'] == payload['checked']


@pytest.mark.asyncio
async def test_delete_checklist_item(client: AsyncClient, db_session: AsyncSession, jwt_token: tuple[str, UserORM]):
    response = await client.delete(f"/checklist/999")
    assert response.status_code == 401

    token, user = jwt_token
    headers = dict(TOKEN=token)
    response = await client.delete(f"/checklist/999", headers=headers)
    assert response.status_code == 404

    checklist_item = await ChecklistORM.create(db_session, text='Хлеб', user_id=user.id)
    response = await client.delete(f"/checklist/{checklist_item.id}", headers=headers)
    assert response.status_code == 200
    assert response.json() == True