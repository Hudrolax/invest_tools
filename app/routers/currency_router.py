from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound, IntegrityError
from fastapi import APIRouter, Depends, HTTPException

from core.db import get_db
from routers import check_token
from models.currency import CurrencyORM
from models.user import UserORM
from . import check_currency_name


class CurrencyBase(BaseModel):
    name: str | None = None


class CurrencyCreate(BaseModel):
    name: str


class CurrencyUpdate(BaseModel):
    name: str


class Currency(CurrencyBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


router = APIRouter(
    prefix="/currencies",
    tags=["currencies"],
    responses={404: {"description": "Currency not found"}},
)


@router.post("/", response_model=Currency)
async def post_currency(
    data: CurrencyCreate,
    user: CurrencyORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> Currency:
    try:
        check_currency_name(data.name, 'Binance-spot')

        return await CurrencyORM.create(db=db, **data.model_dump())
    except (IntegrityError, ValueError) as ex:
        if 'UniqueViolationError' in str(ex):
            raise HTTPException(422, f'Currency with name {data.name} already exists.')
        else:
            raise HTTPException(422, str(ex))


@router.put("/{currency_id}", response_model=Currency)
async def put_currency(
    currency_id: int,
    data: CurrencyUpdate,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> Currency:
    try:
        return await CurrencyORM.update(db=db, id=currency_id, **data.model_dump(exclude_unset=True))
    except NoResultFound:
        raise HTTPException(404, f'Currency with id {currency_id} not found.')
    except (IntegrityError, ValueError) as ex:
        raise HTTPException(422, str(ex))


@router.get("/", response_model=list[Currency])
async def get_currencies(
    db: AsyncSession = Depends(get_db),
    user: UserORM = Depends(check_token),
):
    return await CurrencyORM.get_all(db)


@router.get("/{currency_id}", response_model=Currency)
async def get_currency(
    currency_id: int,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> Currency:
    try:
        return await CurrencyORM.get(db, id=currency_id)
    except NoResultFound:
        raise HTTPException(404, f'Currency with id {currency_id} not found.')


@router.delete("/{currency_id}", response_model=bool)
async def del_currency(
    currency_id: int,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> bool:
    try:
        return await CurrencyORM.delete(db, id=currency_id)
    except NoResultFound as ex:
        raise HTTPException(404, str(ex))
