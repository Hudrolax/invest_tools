from decimal import Decimal
from asyncpg import Connection
from datetime import datetime
from typing import Literal
from .exceptions import NotFoundError, ParamsError
from .users import read_user
from .symbols import read_symbol


async def add_alert(
    conn: Connection,
    user_id: int,
    symbol_id: int,
    price: Decimal,
    trigger: Literal['above', 'below'],
) -> int:
    """Adds an alert into DB

    Args:
        conn (Connection): DB connection
        user_id (int): user id
        symbol_id (int): alert's symbol
        price (Decimal): alert's price
        trigger (Literal): trigger (below, above)

    Returns:
        int: A new alert's id
    """
    # check params
    if trigger != 'below' and trigger != 'above':
        raise ParamsError('trigger param should be "below" or "above"')

    if price <= 0:
        raise ParamsError('Price should be greater then zero.')

    try:
        await read_user(conn, user_id)
    except NotFoundError:
        raise ParamsError(f'User with id {user_id} not found.')

    try:
        await read_symbol(conn, symbol_id)
    except NotFoundError:
        raise ParamsError(f'Symbol with id {symbol_id} not found.')

    # insert the record
    await conn.execute("""
        INSERT INTO
        alerts (symbol_id, price, created_at, triggered_at, trigger, is_active, triggered, user_id, is_sent)
        VALUES ($1, $2, NOW(), NULL, $3, TRUE, FALSE, $4, FALSE)
    """, symbol_id, price, trigger, user_id)
    res = await conn.fetchval('SELECT id FROM alerts ORDER BY id DESC')
    if not res:
        raise ValueError('Insert alert error')

    return res


async def update_alert(
    conn: Connection,
    id: int,
    symbol_id: str | None = None,
    price: Decimal | None = None,
    trigger: str | None = None,
    created_at: datetime | None = None,
    triggered_at: datetime | None = None,
    is_active: bool | None = None,
    triggered: bool | None = None,
    is_sent: bool | None = None,
) -> None:
    """The function updates an alert

    Args:
        conn (Connection): DB connection
        id (int): alert id
        symbol_id (str | None, optional): Symbol id. Defaults to None.
        price (Decimal | None, optional): alert's price. Defaults to None.
        trigger (str | None, optional): trigger (below or above). Defaults to None.
        created_at (datetime | None, optional): Date of creating an alert. Defaults to None.
        triggered_at (datetime | None, optional): Date of triggering an alert. Defaults to None.
        is_active (bool | None, optional): Is an alert is active. Defaults to None.
        triggered (bool | None, optional): Is an alert is triggered. Defaults to None.
        is_sent (bool | None, optional): Is an alert is sent. Defaults to None.
    """    
    if not (symbol_id or price or trigger or created_at or triggered_at or is_active or triggered or is_sent):
        raise ValueError('One of params be passed for updating.)')

    update_fields = []
    values = []

    values.append(id)

    update_params = {
        "symbol_id": symbol_id,
        "price": price,
        "trigger": trigger,
        "created_at": created_at,
        "triggered_at": triggered_at,
        "is_active": is_active,
        "triggered": triggered,
        "is_sent": is_sent,
    }

    for key, value in update_params.items():
        if value:
            values.append(value)
            update_fields.append(f"{key} = ${len(values)}")

    update_clause = ", ".join(update_fields)
    query = f"""
        UPDATE alerts
        SET {update_clause}
        WHERE id = $1
    """

    await conn.execute(query, *values)


async def read_alert(
    conn: Connection,
    id: int
) -> dict:
    """The functions reads the alert from DB

    Args:
        conn (Connection): DB connection
        id (int): DB alert id

    Returns:
        dict: alert record
    """    
    res = await conn.fetchrow("""
        SELECT * FROM alerts
        WHERE id = $1
    """, id)

    if not res:
        raise NotFoundError(f'Alert with id {id} not found.')

    return dict(res)


async def read_alerts(
    conn: Connection,
    user_id: int,
    symbol_id: int | None = None,
    is_sent: bool | None = None,
    is_active: bool | None = None,
    triggerd: bool | None = None,
) -> list:
    """The functions reads alerts from DB

    Args:
        conn (Connection): DB connection
        user_id (int): user id

    Returns:
        list[dict]: list of alert records
    """    
    query_conditions = []
    params = []

    if user_id is not None:
        query_conditions.append("user_id = $1")
        params.append(user_id)

    if symbol_id is not None:
        param_position = len(params) + 1  # Set the correct ordinal position for the parameter
        query_conditions.append(f"symbol_id = ${param_position}")
        params.append(symbol_id)

    if is_sent is not None:
        param_position = len(params) + 1  # Set the correct ordinal position for the parameter
        query_conditions.append(f"is_sent = ${param_position}")
        params.append(is_sent)

    if is_active is not None:
        param_position = len(params) + 1  # Set the correct ordinal position for the parameter
        query_conditions.append(f"is_active = ${param_position}")
        params.append(is_active)

    if triggerd is not None:
        param_position = len(params) + 1  # Set the correct ordinal position for the parameter
        query_conditions.append(f"triggered = ${param_position}")
        params.append(triggerd)
    
    conditions_str = " AND ".join(query_conditions)
    where_clause = f"WHERE {conditions_str}" if conditions_str else ""
    query = f"SELECT * FROM alerts {where_clause} ORDER BY id"
    
    res = await conn.fetch(query, *params)

    return [dict(record) for record in res]


async def delete_alert(
    conn: Connection,
    id: int
) -> None:
    """The functions delete an alert from DB

    Args:
        conn (Connection): DB connection
        id (int): alert id
    """    
    await conn.execute("""
        DELETE FROM alerts
        WHERE id = $1
    """, id)