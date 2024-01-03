from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound, IntegrityError
from fastapi import APIRouter, Depends, HTTPException

from core.db import get_db
from routers import check_token
from models.exin_item import ExInItemORM
from models.user_exin_items import UserExInItemORM
from models.user import UserORM


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
):
    users_exin_items = await UserExInItemORM.get_list(db, user_id=user.id)

    return await ExInItemORM.get_list(db, id=[item.id for item in users_exin_items])


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