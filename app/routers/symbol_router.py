from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends
from decimal import Decimal

from routers import check_token
from core.db import get_db
from models.symbol import SymbolORM
from models.user import UserORM


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


# @router.get("/{symbol_id}", response_model=Symbol)
# async def get_symbol(
#     symbol_id: int,
#     db: AsyncSession = Depends(get_db),
# ) -> Symbol:
#     try:
#         return await SymbolORM.get(db, id=symbol_id)
#     except NoResultFound:
#         raise HTTPException(404, f'Symbol with ID {symbol_id} not found.')


# @router.delete("/{symbol_id}", response_model=bool)
# async def del_symbol(
#     symbol_id: int,
#     db: AsyncSession = Depends(get_db),
# ) -> bool:
#     try:
#         return await SymbolORM.delete(db, id=symbol_id)
#     except NoResultFound:
#         raise HTTPException(404, f'Symbol with ID {symbol_id} not found.')
