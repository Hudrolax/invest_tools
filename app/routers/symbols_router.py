from asyncpg import Connection
from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
from db.db_connection import db
from models.symbols import (
    add_symbol,
    update_symbol,
    read_symbol,
    read_symbols,
    delete_symbol,
)
from models.exceptions import (
    NotFoundError,
    UniqueViolationError,
    ParamsError,
)
from models.symbols_api import Symbol, SymbolWithoutID, Symbols


router = APIRouter(
    prefix="/symbols",
    tags=["symbols"],
    responses={404: {"description": "Symbol not found"}},
)


@router.post("/")
async def post_symbol(
    data: SymbolWithoutID,
    conn: Connection = Depends(db.get_conn),
) -> Symbol:
    try:
        symbol_id = await add_symbol(conn, **dict(data))
        symbol = await read_symbol(conn, symbol_id)
    except UniqueViolationError:
        raise HTTPException(422, 'Symbol + broker not unique.')
    except ParamsError as ex:
        raise HTTPException(422, ex.message)

    return Symbol(**symbol)


@router.put("/{symbol_id}")
async def put_symbol(
    symbol_id: int,
    data: SymbolWithoutID,
    conn: Connection = Depends(db.get_conn),
) -> Symbol:
    try:
        await update_symbol(conn, id=symbol_id, **dict(data))
        symbol = await read_symbol(conn, id=symbol_id)
    except NotFoundError:
        raise HTTPException(404, f'Not found symbol with id {symbol_id}')

    return Symbol(**symbol)


@router.get("/")
async def get_symbols(conn: Connection = Depends(db.get_conn)) -> Symbols:
    symbols = await read_symbols(conn)
    return Symbols(symbols=symbols)


@router.get("/{symbol_id}")
async def get_symbol(
    symbol_id: Annotated[int, "Symbol ID"],
    conn: Connection = Depends(db.get_conn),
) -> Symbol:
    try:
        symbol = await read_symbol(conn, symbol_id)
    except NotFoundError as ex:
        raise HTTPException(404, ex.message)

    return Symbol(**symbol)


@router.delete("/{symbol_id}")
async def del_symbol(
    symbol_id: Annotated[int, "Symbol ID"],
    conn: Connection = Depends(db.get_conn),
) -> dict:
    try:
        await read_symbol(conn, symbol_id)
    except NotFoundError as ex:
        raise HTTPException(404, ex.message)

    await delete_symbol(conn, id=symbol_id)

    return dict(message='ok')
