from pydantic import BaseModel, ConfigDict, validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound, IntegrityError
from sqlalchemy.future import select
from fastapi import APIRouter, Depends, HTTPException
from decimal import Decimal
from datetime import datetime

from . import format_decimal
from core.db import get_db
from routers import check_token
from models.user import UserORM
from models.wallet_transaction import WalletTransactionORM
from models.user_wallets import UserWalletsORM


class TransactionInstanceBase(BaseModel):
    wallet_id: int | None = None
    exin_item_id: int | None = None
    amount: str | None = None
    amountARS: str | None = None
    amountUSD: str | None = None
    amountBTC: str | None = None
    amountETH: str | None = None
    amountRUB: str | None = None
    comment: str | None = None
    date: datetime | None = None

    @validator('amount', 'amountARS', 'amountUSD', 'amountBTC', 'amountETH', 'amountRUB', pre=True)
    def format_decimal_fields(cls, value):
        if value is not None:
            return format_decimal(value)
        return value
    

class TransactionBase(BaseModel):
    wallet_from_id: int | None = None
    wallet_to_id: int | None = None
    exin_item_id: int | None = None
    amount: Decimal
    exchange_rate: Decimal | None = None
    date: datetime | None = None
    comment: str | None = None
    doc_id: str | None = None


class TransactionUpdate(BaseModel):
    wallet_from_id: int | None
    wallet_to_id: int | None
    exin_item_id: int | None
    amount: Decimal
    exchange_rate: Decimal | None
    date: datetime | None = None
    comment: str | None = None


class TransactionCreate(TransactionBase):
    user_id: int


class Transaction(TransactionInstanceBase):
    model_config = ConfigDict(from_attributes=True)
    wallet_id: int
    user_id: int
    # user_name: str
    id: int
    doc_id: str


router = APIRouter(
    prefix="/wallet_transactions",
    tags=["wallet_transactions"],
    responses={404: {"description": "Wallet transaction not found"}},
)

async def create_trz(db: AsyncSession, data: TransactionCreate) -> list[WalletTransactionORM]:
    transaction_records = []
    try:
        if data.wallet_to_id:
            # exchange
            if not data.wallet_from_id:
                raise HTTPException(422, 'wallet_from_id should be passed')
            if not data.wallet_to_id:
                raise HTTPException(422, 'wallet_to_id should be passed')
            if not data.exchange_rate:
                raise HTTPException(422, 'exchange_rate should be passed')
            payload = dict(
                user_id = data.user_id,
                doc_id = data.doc_id,
                comment = data.comment,
                date = data.date,
            )
            wt_from = await WalletTransactionORM.create(db=db, 
                wallet_id = data.wallet_from_id,
                amount = -data.amount,
                **payload
            )
            payload['doc_id'] = wt_from.doc_id # type: ignore
            payload['date'] = wt_from.date # type: ignore
            wt_to = await WalletTransactionORM.create(db=db, 
                wallet_id = data.wallet_to_id,
                amount = data.amount * data.exchange_rate,
                **payload
            )

            transaction_records = [wt_from, wt_to]
        else:
            # regular operation
            if not data.wallet_from_id:
                raise HTTPException(422, 'wallet_from_id should be passed')
            if not data.exin_item_id:
                raise HTTPException(422, 'exin_item_it should be passed')

            payload = dict(
                user_id = data.user_id,
                doc_id = data.doc_id,
                date = data.date,
                wallet_id = data.wallet_from_id,
                exin_item_id = data.exin_item_id,
                amount = data.amount,
                comment = data.comment,
            )
            wt = await WalletTransactionORM.create(db=db, **payload)

            transaction_records = [wt]
        
        return transaction_records
    except IntegrityError as ex:
        raise HTTPException(422, str(ex))


@router.post("/", response_model=list[Transaction])
async def post_wallet_transaction(
    data: TransactionBase,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> list[Transaction]:
    return await create_trz(db, TransactionCreate(user_id=user.id, **data.model_dump(exclude_unset=True))) # type: ignore


@router.put("/{doc_id}", response_model=list[Transaction])
async def put_wallet_transaction(
    doc_id: str,
    data: TransactionUpdate,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> list[WalletTransactionORM]:
    try:
        # get transactions by doc_id and mark deleted
        trz_list = await WalletTransactionORM.get_list(db, doc_id=doc_id)
        if not trz_list:
            raise HTTPException(404, f'Document with id {doc_id} not found.')

        for trz in trz_list:
            await trz.delete_self(db)
        
        data_create = TransactionCreate(doc_id=doc_id, user_id=user.id, **data.model_dump(exclude_unset=True)) # type: ignore

        return await create_trz(db, data_create)
        
    except NoResultFound as ex:
        raise HTTPException(404, str(ex))
    except (IntegrityError, ValueError) as ex:
        raise HTTPException(422, str(ex))


@router.get("/", response_model=list[Transaction])
async def get_wallet_transactions(
    doc_id: str | None = None,
    id: int | None = None,
    wallet_id: int | None = None,
    exin_item_id: int | None = None,
    comment: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: UserORM = Depends(check_token),
    last_n: int = 100
) -> list[WalletTransactionORM]:
    if wallet_id:
        wallet_ids = [wallet_id]
    else:
        # get available wallets for the user
        user_wallets = await UserWalletsORM.get_list(db, user_id=user.id)
        wallet_ids = [uw.wallet_id for uw in user_wallets]

    exin_item_ids = None
    if exin_item_id:
        exin_item_ids = [exin_item_id]
    # else:
    #     # get available exin_items for the user
    #     user_exinitems = await UserExInItemORM.get_list(db, user_id=user.id)
    #     exin_item_ids = [item.exin_item_id for item in user_exinitems]

    # get transactions list for user's wallets
    params = dict(
        doc_id=doc_id,
        id=id,
        wallet_id=wallet_ids,
        exin_item_id=exin_item_ids,
        comment=comment
    )
    if wallet_id:
        params['user_id'] = user.id # type: ignore

    transaction_records = await WalletTransactionORM.get_list(db, 
        **params
    )
    # get last N records
    transaction_records = transaction_records[-last_n:]
    return transaction_records


@router.get("/{doc_id}", response_model=list[Transaction])
async def get_wallet_transaction(
    doc_id: str,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> list[WalletTransactionORM]:
    transaction_records = await WalletTransactionORM.get_list(db, doc_id=doc_id)
    if not transaction_records:
        raise HTTPException(404, f'Document with id {doc_id} not found.')
    return transaction_records


@router.delete("/{doc_id}", response_model=bool)
async def del_wallet_transaction(
    doc_id: str,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> bool:
    # get transactions by doc_id and mark deleted
    trz_list = await WalletTransactionORM.get_list(db, doc_id=doc_id)
    if not trz_list:
        raise HTTPException(404, f'Document with id {doc_id} not found.')

    for trz in trz_list:
        await trz.delete_self(db)
    
    return True