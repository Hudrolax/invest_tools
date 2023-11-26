from asyncpg import Connection
from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
from db.db_connection import db
from models.brokers import (
    add_broker,
    update_broker,
    read_brokers,
    read_broker,
    delete_broker,
)
from models.exceptions import NotFoundError, ParamsError
from models.brokers_api import Brokers, Broker, BrokerWithoutID


router = APIRouter(
    prefix="/brokers",
    tags=["brokers"],
    responses={404: {"description": "Broker not found"}},
)


@router.post("/")
async def post_broker(
    data: BrokerWithoutID,
    conn: Connection = Depends(db.get_conn),
) -> Broker:
    try:
        broker_id = await add_broker(conn, **dict(data))
        broker = await read_broker(conn, broker_id)
    except ParamsError as ex:
        raise HTTPException(422, ex.message)

    return Broker(**broker)


@router.put("/{broker_id}")
async def put_broker(
    broker_id: int,
    data: BrokerWithoutID,
    conn: Connection = Depends(db.get_conn),
) -> Broker:
    try:
        await update_broker(conn, id=broker_id, **dict(data))
        broker = await read_broker(conn, id=broker_id)
    except ParamsError as ex:
        raise HTTPException(422, ex.message)

    return Broker(**broker)


@router.get("/")
async def get_brokers(conn: Connection = Depends(db.get_conn)) -> Brokers:
    brokers = await read_brokers(conn)
    return Brokers(brokers=brokers)


@router.get("/{broker_id}")
async def get_broker(
    broker_id: Annotated[int, "Broker ID"],
    conn: Connection = Depends(db.get_conn),
) -> Broker:
    try:
        broker = await read_broker(conn, broker_id)
    except NotFoundError as ex:
        raise HTTPException(404, ex.message)

    return Broker(**broker)


@router.delete("/{broker_id}")
async def del_broker(
    broker_id: Annotated[int, "Broker ID"],
    conn: Connection = Depends(db.get_conn),
) -> dict:
    try:
        await read_broker(conn, broker_id)
    except NotFoundError as ex:
        raise HTTPException(404, ex.message)

    await delete_broker(conn, id=broker_id)

    return dict(message='ok')
