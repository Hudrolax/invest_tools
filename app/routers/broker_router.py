from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound, IntegrityError
from fastapi import APIRouter, Depends, HTTPException

from core.db import get_db
from routers import check_token
from models.broker import BrokerORM
from models.user import UserORM


class BrokerBase(BaseModel):
    name: str | None = None


class BrokerCreate(BrokerBase):
    pass


class BrokerUpdate(BrokerBase):
    pass


class Broker(BrokerBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


router = APIRouter(
    prefix="/brokers",
    tags=["brokers"],
    responses={404: {"description": "Broker not found"}},
)


@router.post("/", response_model=Broker)
async def post_broker(
    data: BrokerCreate,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> Broker:
    try:
        return await BrokerORM.create(db=db, **data.model_dump())
    except IntegrityError as ex:
        raise HTTPException(422, str(ex))


@router.put("/{broker_id}", response_model=Broker)
async def put_broker(
    broker_id: int,
    data: BrokerUpdate,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> Broker:
    try:
        return await BrokerORM.update(db=db, id=broker_id, **data.model_dump(exclude_unset=True))
    except NoResultFound:
        raise HTTPException(404, f'Broker with id {broker_id} not found.')
    except (IntegrityError, ValueError) as ex:
        raise HTTPException(422, str(ex))


@router.get("/", response_model=list[Broker])
async def get_brokers(
    db: AsyncSession = Depends(get_db),
    user: UserORM = Depends(check_token),
):
    return await BrokerORM.get_all(db)


@router.get("/{broker_id}", response_model=Broker)
async def get_broker(
    broker_id: int,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> Broker:
    try:
        return await BrokerORM.get(db, id=broker_id)
    except NoResultFound:
        raise HTTPException(404, f'Broker with id {broker_id} not found.')


@router.delete("/{broker_id}", response_model=bool)
async def del_broker(
    broker_id: int,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> bool:
    try:
        return await BrokerORM.delete(db, id=broker_id)
    except NoResultFound as ex:
        raise HTTPException(404, str(ex))