from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound, IntegrityError
from sqlalchemy.orm import attributes as orm_attributes
from fastapi import APIRouter, Depends, HTTPException
from decimal import Decimal
from datetime import datetime

from brokers.binance import binance_symbols
from routers import check_token, telegram_bot_authorized
from core.db import get_db
from models.alert import AlertORM, Triggers
from models.user import UserORM
from models.symbol import SymbolORM


class AlertBase(BaseModel):
    symbol_id: int
    symbol_name: str
    user_id: int
    price: Decimal
    trigger: Triggers
    comment: str | None = None


class AlertCreate(BaseModel):
    symbol_name: str
    broker_name: str
    price: Decimal
    trigger: Triggers
    comment: str | None = None


class AlertUpdate(BaseModel):
    symbol_name: str | None = None
    symbol_id: str | None = None
    price: Decimal | None = None
    trigger: Triggers | None = None
    created_at: datetime | None = None
    triggered_at: datetime | None = None
    is_active: bool | None = None
    is_sent: bool | None = None


class Alert(AlertBase):
    # model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    triggered_at: datetime | None = None
    is_active: bool = True
    is_sent: bool = False

router = APIRouter(
    prefix="/alerts",
    tags=["alerts"],
    responses={404: {"description": "Alert not found"}},
)

def check_symbol_name(symbol_name: str, broker_name: str):
    if not symbol_name in binance_symbols[broker_name]:
        raise ValueError(f'Unexisiting symbol with name {symbol_name}')


@router.post("/", response_model=Alert)
async def post_alert(
    data: AlertCreate,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> Alert:
    try:
        check_symbol_name(data.symbol_name, data.broker_name)

        alert = await AlertORM.create(db=db, user_id=user.id, **data.model_dump())
        symbol = await SymbolORM.get(db, alert.symbol_id) # type: ignore
        alert_dict = orm_attributes.instance_dict(alert)
        alert_dict['symbol_name'] = symbol.name
        return Alert(**alert_dict)
    except (IntegrityError, ValueError, KeyError) as ex:
        raise HTTPException(422, str(ex))


@router.put("/{alert_id}", response_model=Alert)
async def put_alert(
    alert_id: int,
    data: AlertUpdate,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> Alert:
    try:
        alert = await AlertORM.get(db, alert_id)
        if alert.user_id != user.id: # type: ignore
            raise HTTPException(401, 'Wrong TOKEN')

        alert =  await AlertORM.update(db=db, id=alert_id, **data.model_dump(exclude_unset=True))
        symbol = await SymbolORM.get(db, alert.symbol_id) # type: ignore
        alert_dict = orm_attributes.instance_dict(alert)
        alert_dict['symbol_name'] = symbol.name
        return Alert(**alert_dict)
    except NoResultFound:
        raise HTTPException(404, f'Alert with id {alert_id} not dound.')
    except (IntegrityError, ValueError) as ex:
        raise HTTPException(422, str(ex))


@router.get("/", response_model=list[Alert])
async def get_alerts(
    broker_name: str | None = None,
    symbol_name: str | None = None,
    is_sent: bool | None = None,
    is_active: bool | None = None,
    is_triggered: bool | None = None,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> list[Alert]:
    try:
        alerts = await AlertORM.get_filtered_alerts(
            db,
            user,
            broker_name, 
            symbol_name,
            is_active,
            is_sent,
            is_triggered,
        )
        alert_list = []
        for alert in alerts:
            alert_dict = orm_attributes.instance_dict(alert)
            alert_dict['symbol_name'] = alert.symbol.name
            alert_list.append(Alert(**alert_dict))

        return alert_list
    except (IntegrityError, ValueError) as ex:
        raise HTTPException(422, str(ex))

@router.get("/telegram_bot_api/", response_model=list[Alert])
async def get_alerts_telegram_bot_api(
    broker_name: str | None = None,
    symbol_name: str | None = None,
    is_sent: bool | None = None,
    is_active: bool | None = None,
    is_triggered: bool | None = None,
    authorized: bool = Depends(telegram_bot_authorized),
    db: AsyncSession = Depends(get_db),
) -> list[Alert]:
    try:
        alerts = await AlertORM.get_filtered_alerts(
            db=db,
            broker_name=broker_name, 
            symbol_name=symbol_name,
            is_active=is_active,
            is_sent=is_sent,
            is_triggered=is_triggered,
        )
        alert_list = []
        for alert in alerts:
            alert_dict = orm_attributes.instance_dict(alert)
            alert_dict['symbol_name'] = alert.symbol.name
            alert_list.append(Alert(**alert_dict))

        return alert_list
    except (IntegrityError, ValueError) as ex:
        raise HTTPException(422, str(ex))


@router.get("/{alert_id}", response_model=Alert)
async def get_alert(
    alert_id: int,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> Alert:
    try:
        alert = await AlertORM.get(db, id=alert_id)
        if alert.user_id != user.id: # type: ignore
            raise HTTPException(401, 'Wrong TOKEN')

        alert_dict = orm_attributes.instance_dict(alert)
        alert_dict['symbol_name'] = alert.symbol.name

        return Alert(**alert_dict)
    except NoResultFound:
        raise HTTPException(404, f'Alert with id {alert_id} not dound.')


@router.delete("/{alert_id}", response_model=bool)
async def del_alert(
    alert_id: int,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> bool:
    try:
        alert = await AlertORM.get(db, id=alert_id)
        if alert.user_id != user.id: # type: ignore
            raise HTTPException(401, 'Wrong TOKEN')

        return await AlertORM.delete(db, id=alert_id)
    except NoResultFound:
        raise HTTPException(404, f'Alert with id {alert_id} not dound.')
    except Exception as ex:
        raise HTTPException(500, str(ex))