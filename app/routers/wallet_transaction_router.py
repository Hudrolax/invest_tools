from pydantic import BaseModel, ConfigDict, validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound, IntegrityError
from sqlalchemy import select, func, case, desc
from fastapi import APIRouter, Depends, HTTPException
from decimal import Decimal
from datetime import datetime

from . import format_decimal
from core.db import get_db
from routers import check_token
from models.user import UserORM
from models.wallet_transaction import WalletTransactionORM
from models.wallet import WalletORM
from models.exin_item import ExInItemORM
from models.currency import CurrencyORM


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
    wallet_id: int  # type: ignore
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
                user_id=data.user_id,
                doc_id=data.doc_id,
                comment=data.comment,
                date=data.date,
            )
            wt_from = await WalletTransactionORM.create(db=db,
                                                        wallet_id=data.wallet_from_id,
                                                        amount=-data.amount,
                                                        **payload
                                                        )
            payload['doc_id'] = wt_from.doc_id  # type: ignore
            payload['date'] = wt_from.date  # type: ignore
            wt_to = await WalletTransactionORM.create(db=db,
                                                      wallet_id=data.wallet_to_id,
                                                      amount=data.amount * data.exchange_rate,
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
                user_id=data.user_id,
                doc_id=data.doc_id,
                date=data.date,
                wallet_id=data.wallet_from_id,
                exin_item_id=data.exin_item_id,
                amount=data.amount,
                comment=data.comment,
            )
            wt = await WalletTransactionORM.create(db=db, **payload)

            transaction_records = [wt]

        return transaction_records
    except IntegrityError as ex:
        raise HTTPException(422, str(ex))


@router.post("/")
async def post_wallet_transaction(
    data: TransactionBase,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> bool:
    # add transaction
    await create_trz(db, TransactionCreate(user_id=user.id, **data.model_dump(exclude_unset=True))) # type: ignore

    return True


@router.put("/{doc_id}", response_model=bool)
async def put_wallet_transaction(
    doc_id: str,
    data: TransactionUpdate,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> bool:
    try:
        # get transactions by doc_id and mark deleted
        trz_list = await WalletTransactionORM.get_list(db, doc_id=doc_id)
        if not trz_list:
            raise HTTPException(404, f'Document with id {doc_id} not found.')

        for trz in trz_list:
            await trz.delete_self(db)

        data_create = TransactionCreate(
            doc_id=doc_id, user_id=user.id, **data.model_dump(exclude_unset=True)) # type: ignore

        await create_trz(db, data_create)
        return True

    except NoResultFound as ex:
        raise HTTPException(404, str(ex))
    except (IntegrityError, ValueError) as ex:
        raise HTTPException(422, str(ex))


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


@router.get("/")
async def get_wallet_transactions(
    currency_name: str,
    date: str | None = None,
    filter: str = "",
    db: AsyncSession = Depends(get_db),
    user: UserORM = Depends(check_token)
):
    from_condition = (((WalletTransactionORM.exin_item_id == None) &
                       (WalletTransactionORM.amount < 0)) |
                      (WalletTransactionORM.exin_item_id != None))
    to_condition = ((WalletTransactionORM.exin_item_id == None) &
                    (WalletTransactionORM.amount >= 0))

    amount = getattr(WalletTransactionORM, f'amount{currency_name}')
    wallet_from_case = case((from_condition, WalletTransactionORM.wallet_id))
    wallet_to_case = case((to_condition, WalletTransactionORM.wallet_id))
    amount_from_case = case(
        (from_condition, case((
            WalletTransactionORM.exin_item_id == None, WalletTransactionORM.amount
        ), else_=amount)
        )
    )
    amount_to_case = case((to_condition, WalletTransactionORM.amount))

    filter_condition = True
    if filter:
        filter_condition = (
            (WalletTransactionORM.comment.ilike(f'%{filter}%'))
            | (ExInItemORM.name.ilike(f'%{filter}%'))
        ) 
    elif date:
        if date:
            date_limit = datetime.fromisoformat(date)
            filter_condition = WalletTransactionORM.date >= date_limit
        else:
            raise Exception("Date not filled")

    query_trz = (
        select(
            WalletTransactionORM.doc_id,
            ExInItemORM.income.label("exin_item_income"),
            func.max(ExInItemORM.name).label("exin_item_name"),
            func.max(WalletTransactionORM.user_id).label("user_id"),
            func.max(WalletTransactionORM.date).label("datetime"),
            func.max(func.date(WalletTransactionORM.date)).label("date"),
            func.max(WalletTransactionORM.exin_item_id).label("exin_item_id"),
            func.max(wallet_from_case).label('wallet_from_id'),
            func.max(wallet_to_case).label('wallet_to_id'),
            func.sum(amount_from_case).label('amount_from'),
            func.sum(amount_to_case).label('amount_to'),
            func.max(WalletTransactionORM.comment).label("comment"),
            func.max(UserORM.name).label("user_name"),
        )
        .select_from(WalletTransactionORM)
        .join(UserORM, (UserORM.id == WalletTransactionORM.user_id) & (UserORM.family_group == user.family_group))
        .outerjoin(ExInItemORM, ExInItemORM.id == WalletTransactionORM.exin_item_id)
        .where(filter_condition) # type: ignore
        .group_by(WalletTransactionORM.doc_id, "exin_item_income")
    ).alias()

    # Создаем псевдонимы для таблиц
    wallet_from = WalletORM.__table__.alias("wallet_from")
    wallet_from_currency = CurrencyORM.__table__.alias("wallet_from_currency")
    wallet_to = WalletORM.__table__.alias("wallet_to")
    wallet_to_currency = CurrencyORM.__table__.alias("wallet_to_currency")

    query_main = (
        select(
            query_trz.c.doc_id,
            query_trz.c.date,
            query_trz.c.datetime,
            query_trz.c.exin_item_id,
            query_trz.c.exin_item_name,
            query_trz.c.exin_item_income,
            query_trz.c.wallet_from_id,
            wallet_from.c.name.label("wallet_from_name"),
            wallet_from.c.balance.label("wallet_from_balance"),
            wallet_from_currency.c.id.label("wallet_from_currency_id"),
            wallet_from_currency.c.name.label("wallet_from_currency_name"),
            query_trz.c.wallet_to_id,
            wallet_to.c.name.label("wallet_to_name"),
            wallet_to.c.balance.label("wallet_to_balance"),
            wallet_to_currency.c.id.label("wallet_to_currency_id"),
            wallet_to_currency.c.name.label("wallet_to_currency_name"),
            query_trz.c.amount_from,
            query_trz.c.amount_to,
            query_trz.c.comment,
            query_trz.c.user_id,
            query_trz.c.user_name,
        )
        .select_from(query_trz)
        .join(wallet_from, wallet_from.c.id == query_trz.c.wallet_from_id)
        .join(wallet_from_currency, wallet_from_currency.c.id == wallet_from.c.currency_id)
        .outerjoin(wallet_to, wallet_to.c.id == query_trz.c.wallet_to_id)
        .outerjoin(wallet_to_currency, wallet_to_currency.c.id == wallet_to.c.currency_id)
        .order_by(desc(query_trz.c.datetime))
    ).alias()

    query = (
        select(
            query_main.c.date,
            func.sum(query_main.c.amount_from).label("day_amount"),
            func.array_agg(
                func.json_build_object(
                    'doc_id', query_main.c.doc_id,
                    'datetime', query_main.c.datetime,
                    'date', query_main.c.date,
                    'user', func.json_build_object(
                        'id', query_main.c.user_id,
                        'name', query_main.c.user_name,
                    ),
                    'exin_item', func.json_build_object(
                        'id', query_main.c.exin_item_id,
                        'name', query_main.c.exin_item_name,
                        'income', query_main.c.exin_item_income,
                    ),
                    'wallet_from', func.json_build_object(
                        'id', query_main.c.wallet_from_id,
                        'name', query_main.c.wallet_from_name,
                        'balance', query_main.c.wallet_from_balance,
                        'currency', func.json_build_object(
                            'id', query_main.c.wallet_from_currency_id,
                            'name', query_main.c.wallet_from_currency_name,
                        ),
                    ),
                    'wallet_to', func.json_build_object(
                        'id', query_main.c.wallet_to_id,
                        'name', query_main.c.wallet_to_name,
                        'balance', query_main.c.wallet_to_balance,
                        'currency', func.json_build_object(
                            'id', query_main.c.wallet_to_currency_id,
                            'name', query_main.c.wallet_to_currency_name,
                        ),
                    ),
                    'amount_from', query_main.c.amount_from,
                    'amount_to', query_main.c.amount_to,
                    'comment', query_main.c.comment,
                )
            ).label("day_transactions")
        )
        .group_by(query_main.c.date)
        .order_by(desc(query_main.c.date))
    )

    result = (await db.execute(query)).mappings().all()
    return result
