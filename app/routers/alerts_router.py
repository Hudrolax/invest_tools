from asyncpg import Connection
from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
from db.db_connection import db
from models.alerts import (
    add_alert,
    update_alert,
    read_alert,
    read_alerts,
    delete_alert,
)
from models.exceptions import NotFoundError, UniqueViolationError, ParamsError
from models.alerts_api import Alert, NewAlertWithoutId, Alert, AlertUpdate, Alerts


router = APIRouter(
    prefix="/alerts",
    tags=["alerts"],
    responses={404: {"description": "Alert not found"}},
)


@router.post("/")
async def post_alert(
    data: NewAlertWithoutId,
    conn: Connection = Depends(db.get_conn),
) -> Alert:
    try:
        alert_id = await add_alert(conn, **dict(data))
        alert = await read_alert(conn, alert_id)
    except ParamsError as ex:
        raise HTTPException(422, ex.message)

    return Alert(**alert)


@router.put("/{alert_id}")
async def put_alert(
    alert_id: int,
    data: AlertUpdate,
    conn: Connection = Depends(db.get_conn),
) -> Alert:
    try:
        await update_alert(conn, id=alert_id, **dict(data))
        alert = await read_alert(conn, id=alert_id)
    except ParamsError as ex:
        raise HTTPException(422, ex.message)

    return Alert(**alert)


@router.get("/")
async def get_alerts(user_id: int, conn: Connection = Depends(db.get_conn)) -> Alerts:
    alerts = await read_alerts(conn, user_id)
    return Alerts(alerts=alerts)


@router.get("/{alert_id}")
async def get_alert(
    alert_id: Annotated[int, "Alert ID"],
    conn: Connection = Depends(db.get_conn),
) -> Alert:
    try:
        alert = await read_alert(conn, alert_id)
    except NotFoundError as ex:
        raise HTTPException(404, ex.message)

    return Alert(**alert)


@router.delete("/{alert_id}")
async def del_alert(
    alert_id: Annotated[int, "Alert ID"],
    conn: Connection = Depends(db.get_conn),
) -> dict:
    try:
        await read_alert(conn, alert_id)
    except NotFoundError as ex:
        raise HTTPException(404, ex.message)

    await delete_alert(conn, id=alert_id)

    return dict(message='ok')