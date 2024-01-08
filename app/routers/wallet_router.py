from pydantic import BaseModel, ConfigDict, validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound, IntegrityError
from fastapi import APIRouter, Depends, HTTPException
from decimal import Decimal

from . import format_decimal
from core.db import get_db
from routers import check_token
from models.wallet import WalletORM
from models.user import UserORM
from models.user_wallets import UserWalletsORM



class WalletBase(BaseModel):
    name: str | None = None
    currency_id: int | None = None
    balance: Decimal | None = None

class WalletCreate(BaseModel):
    name: str
    currency_id: int


class WalletUpdate(WalletBase):
    pass


class Wallet(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    currency_id: int
    balance: str

    @validator('balance', pre=True)
    def format_balance(cls, v):
        return format_decimal(v)


router = APIRouter(
    prefix="/wallets",
    tags=["wallets"],
    responses={404: {"description": "Wallet not found"}},
)


@router.post("/", response_model=Wallet)
async def post_wallet(
    data: WalletCreate,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> Wallet:
    try:
        return await WalletORM.create(db=db, user_id=user.id, **data.model_dump())
    except IntegrityError as ex:
        raise HTTPException(422, str(ex))


@router.put("/{wallet_id}", response_model=Wallet)
async def put_wallet(
    wallet_id: int,
    data: WalletUpdate,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> Wallet:
    try:
        user_wallets = await UserWalletsORM.get_list(db, user_id=user.id)
        if not user_wallets:
            raise HTTPException(404, "Wallet not found")

        return await WalletORM.update(db=db, id=wallet_id, **data.model_dump(exclude_unset=True))
    except NoResultFound:
        raise HTTPException(404, f'Wallet with id {wallet_id} not found.')
    except (IntegrityError, ValueError) as ex:
        raise HTTPException(422, str(ex))


@router.get("/", response_model=list[Wallet])
async def get_wallets(
    db: AsyncSession = Depends(get_db),
    user: UserORM = Depends(check_token),
):
    user_wallets = await UserWalletsORM.get_list(db, user_id=user.id)

    return await WalletORM.get_list(db, id=[item.wallet_id for item in user_wallets])


@router.get("/{wallet_id}", response_model=Wallet)
async def get_wallet(
    wallet_id: int,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> Wallet:
    try:
        user_wallets = await UserWalletsORM.get_list(db, user_id=user.id)
        if not user_wallets:
            raise HTTPException(404, "Wallet not found")

        return await WalletORM.get(db, id=wallet_id)
    except NoResultFound:
        raise HTTPException(404, f'Wallet with id {wallet_id} not found.')


@router.delete("/{wallet_id}", response_model=bool)
async def del_wallet(
    wallet_id: int,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> bool:
    try:
        user_wallets = await UserWalletsORM.get_list(db, user_id=user.id)
        if not user_wallets:
            raise HTTPException(404, "Wallet not found")

        return await WalletORM.delete(db, id=wallet_id)
    except NoResultFound as ex:
        raise HTTPException(404, str(ex))