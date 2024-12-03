from pydantic import BaseModel, ConfigDict, validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound
from sqlalchemy import select, desc, func, case
from fastapi import APIRouter, Depends
from decimal import Decimal
from brokers.bybit import BybitBroker, OrderSide

from routers import check_token, format_decimal
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
    base_coin: str
    quote_coin: str
    orders_buy_count: int | None = None
    orders_buy_size: str | None = None
    orders_sell_count: int | None = None
    orders_sell_size: str | None = None
    position_size: str | None = None
    position_side: OrderSide | None = None
    pnl: str | None = None
    pnl_percent: str | None = None

    @validator(
        "orders_buy_size",
        "orders_sell_size",
        "position_size",
        "pnl",
        "pnl_percent",
        pre=True,
    )
    def format_decimal_fields(cls, value):
        return format_decimal(value)


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

        def create_order_query(order_side):
            return (
                select(
                    SymbolORM.id.label("id"),
                    func.count(OrderORM.id).label("orders_count"),
                    func.sum(
                        case(
                            (
                                SymbolORM.contract_type == "InversePerpetual",
                                OrderORM.leaves_qty,
                            ),
                            else_=OrderORM.leaves_value,
                        )
                    ).label("orders_size"),
                )
                .select_from(SymbolORM)
                .join(
                    OrderORM,
                    (OrderORM.symbol_id == SymbolORM.id)
                    & ((OrderORM.order_status == "New") | (OrderORM.order_status == "PartiallyFilled"))
                    & (OrderORM.side == order_side),
                )
                .group_by(SymbolORM.id)
            ).alias()

        query_orders_buy = create_order_query("Buy")
        query_orders_sell = create_order_query("Sell")

        query_position = (
            select(
                SymbolORM.id,
                func.max(
                    case(
                        (
                            SymbolORM.contract_type == "InversePerpetual",
                            PositionORM.size,
                        ),
                        else_=PositionORM.position_value,
                    )
                ).label("position_size"),
                func.max(
                    case(
                        (
                            SymbolORM.contract_type == "InversePerpetual",
                            (PositionORM.unrealised_pnl + PositionORM.cur_realised_pnl) * PositionORM.mark_price,
                        ),
                        else_=PositionORM.unrealised_pnl + PositionORM.cur_realised_pnl,
                    ),
                ).label("pnl"),
                func.max(
                    case(
                        (
                            SymbolORM.contract_type == "InversePerpetual",
                            (PositionORM.unrealised_pnl + PositionORM.cur_realised_pnl) / PositionORM.size * PositionORM.mark_price * PositionORM.leverage * 100,
                        ),
                        else_=(PositionORM.unrealised_pnl + PositionORM.cur_realised_pnl) / PositionORM.position_value * PositionORM.leverage *  100,
                    )
                ).label("pnl_percent"),
                func.max(PositionORM.side).label("side"),
            )
            .select_from(SymbolORM)
            .join(PositionORM, PositionORM.symbol_id == SymbolORM.id)
            .group_by(SymbolORM.id)
        ).alias()

        query = (
            select(
                SymbolORM.name.label("symbol"),
                SymbolORM.base_coin,
                SymbolORM.quote_coin,
                func.max(query_orders_buy.c.orders_count).label("orders_buy_count"),
                func.max(query_orders_buy.c.orders_size).label("orders_buy_size"),
                func.max(query_orders_sell.c.orders_count).label("orders_sell_count"),
                func.max(query_orders_sell.c.orders_size).label("orders_sell_size"),
                func.max(query_position.c.position_size).label("position_size"),
                func.max(query_position.c.side).label("position_side"),
                func.max(query_position.c.pnl).label("pnl"),
                func.max(query_position.c.pnl_percent).label("pnl_percent"),
            )
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
                ((PositionORM.user_id == user.id) & (PositionORM.symbol_id == SymbolORM.id)),
                isouter=True,
            )
            .join(
                LineORM,
                (LineORM.user_id == user.id) & (LineORM.symbol_id == SymbolORM.id),
                isouter=True,
            )
            .group_by(SymbolORM.id)  # Группировка по идентификатору символа
            .join(query_orders_buy, query_orders_buy.c.id == SymbolORM.id, isouter=True)
            .join(query_orders_sell, query_orders_sell.c.id == SymbolORM.id, isouter=True)
            .join(query_position, query_position.c.id == SymbolORM.id, isouter=True)
            .order_by(
                desc(func.bool_or(PositionORM.id.isnot(None))),  # Затем символы с позициями
                desc(func.bool_or(OrderORM.id.isnot(None))),  # Сначала символы с ордерами
                desc(func.bool_or(LineORM.id.isnot(None))),  # Затем символы с линиями
                SymbolORM.name,  # И только потом по имени
            )
        )
        result = (await db.execute(query)).mappings().all()
        return [TradingSymbol(**item) for item in result]

    except NoResultFound:
        return []
