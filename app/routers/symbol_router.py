from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound
from sqlalchemy import select, desc, func
from fastapi import APIRouter, Depends
from decimal import Decimal
from brokers.bybit import BybitBroker

from routers import check_token
from core.db import get_db
from models.symbol import SymbolORM
from models.user import UserORM
from models.broker import BrokerORM
from models.order import OrderORM
from models.position import PositionORM
from models.lines import LineORM


class SymbolBase(BaseModel):
    name: str
    broker_id: int
    rate: Decimal | None = None


class SymbolCreate(SymbolBase):
    pass


class SymbolUpdate(BaseModel):
    name: str | None = None
    broker_id: int | None = None


class Symbol(SymbolBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class TradingSymbol(BaseModel):
    symbol: str


router = APIRouter(
    prefix="/symbols",
    tags=["symbols"],
    responses={404: {"description": "Symbol not found"}},
)


# @router.put("/{symbol_id}", response_model=Symbol)
# async def put_symbol(
#     symbol_id: int,
#     data: SymbolUpdate,
#     db: AsyncSession = Depends(get_db),
# ) -> Symbol:
#     try:
#         return await SymbolORM.update(db=db, id=symbol_id, **data.model_dump(exclude_unset=True))
#     except NoResultFound:
#         raise HTTPException(404, f'Symbol with ID {symbol_id} not found.')
#     except IntegrityError as ex:
#         raise HTTPException(422, str(ex.orig))


@router.get("/", response_model=list[Symbol])
async def get_symbols(
    user: UserORM = Depends(check_token),
    symbol_ids: list[int] | None = None,
    symbol_names: list[str] | None = None,
    broker_name: str | None = None,
    currecnies_names: list[str] | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[SymbolORM]:
    return await SymbolORM.get_list(
        db=db,
        symbol_ids=symbol_ids,
        symbol_names=symbol_names,
        broker_name=broker_name,
        currecnies_names=currecnies_names,
    )


@router.get("/trading_symbols/{broker}", response_model=list[TradingSymbol])
async def get_symbols_by_broker(
    broker: BybitBroker,
    db: AsyncSession = Depends(get_db),
    user: UserORM = Depends(check_token),
) -> list[TradingSymbol]:
    try:
        query = (
            select(SymbolORM.name.label("symbol"))
            .select_from(SymbolORM)
            .join(
                BrokerORM,
                (BrokerORM.id == SymbolORM.broker_id) & (BrokerORM.name == broker),
            )
            .join(
                OrderORM,
                (OrderORM.user_id == user.id) & (OrderORM.symbol_id == SymbolORM.id),
                isouter=True,
            )
            .join(
                PositionORM,
                (
                    (PositionORM.user_id
                    == user.id) & (PositionORM.symbol_id
                    == SymbolORM.id)
                ),
                isouter=True,
            )
            .join(
                LineORM,
                (LineORM.user_id == user.id) & (LineORM.symbol_id == SymbolORM.id),
                isouter=True,
            )
            .group_by(SymbolORM.id)  # Группировка по идентификатору символа
            .order_by(
                desc(
                    func.bool_or(OrderORM.id.isnot(None))
                ),  # Сначала символы с ордерами
                desc(
                    func.bool_or(PositionORM.id.isnot(None))
                ),  # Затем символы с позициями
                desc(func.bool_or(LineORM.id.isnot(None))),  # Затем символы с линиями
                SymbolORM.name,  # И только потом по имени
            )
        )
        result = (await db.execute(query)).mappings().all()
        return [TradingSymbol(symbol=item["symbol"]) for item in result]

    except NoResultFound:
        return []
