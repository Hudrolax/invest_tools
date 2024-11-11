from pydantic import BaseModel, ConfigDict, validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound, IntegrityError
from sqlalchemy import select, func, case

from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import date, timedelta

from core.db import get_db
from routers import check_token, format_decimal
from models.exin_item import ExInItemORM
from models.user_exin_items import UserExInItemORM
from models.wallet_transaction import WalletTransactionORM
from models.user import UserORM
from models.currency import CurrencyORM


class ExInItemBase(BaseModel):
    name: str | None = None
    income: bool | None = None


class ExInItemCreate(BaseModel):
    name: str
    income: bool


class ExInItemUpdate(BaseModel):
    name: str
    income: bool


class ExInItem(ExInItemBase):
    model_config = ConfigDict(from_attributes=True)
    id: int

class HomeScreenItem(BaseModel):
    id: int
    name: str
    amount: str

    @validator('amount', pre=True)
    def format_decimal_fields(cls, value):
        if value is not None:
            return format_decimal(value)
        return value

router = APIRouter(
    prefix="/exin_items",
    tags=["exin_items"],
    responses={404: {"description": "ExInItem not found"}},
)


@router.post("/", response_model=ExInItem)
async def post_exin_item(
    data: ExInItemCreate,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> ExInItem:
    try:
        return await ExInItemORM.create(db=db, user_id=user.id, **data.model_dump())
    except IntegrityError as ex:
        raise HTTPException(422, str(ex))


@router.put("/{exin_item_id}", response_model=ExInItem)
async def put_exin_item(
    exin_item_id: int,
    data: ExInItemUpdate,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> ExInItem:
    try:
        users_exin_items = await UserExInItemORM.get_list(db, user_id=user.id, exin_item_id=exin_item_id)
        if not users_exin_items:
            raise HTTPException(404, "ExInItem not found")

        return await ExInItemORM.update(db=db, id=exin_item_id, **data.model_dump(exclude_unset=True))
    except NoResultFound:
        raise HTTPException(404, f'ExInItem with id {exin_item_id} not found.')
    except (IntegrityError, ValueError) as ex:
        raise HTTPException(422, str(ex))


@router.get("/", response_model=list[ExInItem])
async def get_exin_items(
    db: AsyncSession = Depends(get_db),
    user: UserORM = Depends(check_token),
    ids: list[int] | None = Query(None)
) -> list[ExInItemORM]:
    user_exin_items = await UserExInItemORM.get_list(db, user_id=user.id)
    ids_list = [item.exin_item_id for item in user_exin_items]

    if ids:
        for id in ids:
            if id not in ids_list:
                ids_list.append(id)  # type: ignore

    return await ExInItemORM.get_list(db, id=ids_list)


@router.get("/{exin_item_id}", response_model=ExInItem)
async def get_exin_item(
    exin_item_id: int,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> ExInItem:
    try:
        users_exin_items = await UserExInItemORM.get_list(db, user_id=user.id, exin_item_id=exin_item_id)
        if not users_exin_items:
            raise HTTPException(404, "ExInItem not found")

        return await ExInItemORM.get(db, id=exin_item_id)
    except NoResultFound:
        raise HTTPException(404, f'ExInItem with id {exin_item_id} not found.')


@router.delete("/{exin_item_id}", response_model=bool)
async def del_exin_item(
    exin_item_id: int,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> bool:
    try:
        users_exin_items = await UserExInItemORM.get_list(db, user_id=user.id, exin_item_id=exin_item_id)
        if not users_exin_items:
            raise HTTPException(404, "ExInItem not found")

        return await ExInItemORM.delete(db, id=exin_item_id)
    except NoResultFound as ex:
        raise HTTPException(404, str(ex))


@router.get("/home_screen_items/", response_model=list[HomeScreenItem])
async def get_exin_items_for_home_screen(
    currency_name: str,
    income: bool,
    db: AsyncSession = Depends(get_db),
    user: UserORM = Depends(check_token),
) -> list[HomeScreenItem]:
    currency = await CurrencyORM.get_by_name(db, name=currency_name)
    if not currency:
        raise HTTPException(422, f'Currency with name "{currency_name}" not found.')

    thirty_days_ago = date.today() - timedelta(days=30)

    amount_query = (
        select(
            func.sum(getattr(WalletTransactionORM,f'amount{currency_name}')).label('amount'),
            ExInItemORM.id,
        )
        .select_from(WalletTransactionORM)
        .join(ExInItemORM, ExInItemORM.id == WalletTransactionORM.exin_item_id)
        .join(UserORM, (UserORM.family_group == user.family_group) & (UserORM.id == WalletTransactionORM.user_id))
        .where((ExInItemORM.income == income) & (WalletTransactionORM.date >= thirty_days_ago))
        .group_by(ExInItemORM.id)
    ).alias()

    query = (
        select(
            ExInItemORM.id,
            ExInItemORM.name,
            func.max(case((amount_query.c.amount.is_(None), 0), else_=amount_query.c.amount)).label('amount'),
        )
        .select_from(ExInItemORM)
        .join(UserExInItemORM, UserExInItemORM.exin_item_id == ExInItemORM.id)
        .join(UserORM, (UserORM.id == UserExInItemORM.user_id) & (UserORM.family_group == user.family_group))
        .outerjoin(amount_query, amount_query.c.id == ExInItemORM.id)
        .where(ExInItemORM.income == income)
        .group_by(ExInItemORM.id, ExInItemORM.name)
        .order_by(ExInItemORM.id)
    )

    result = (await db.execute(query)).mappings().all()

    return [HomeScreenItem(**item) for item in result]
