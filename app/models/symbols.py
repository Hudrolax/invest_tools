from asyncpg import Connection
from asyncpg.exceptions import UniqueViolationError
import re
from .exceptions import (
    NotFoundError,
    UniqueViolationError as OwnUniqueViolationError,
    ParamsError,
)
from .brokers import read_broker

def check_symbol_name(input_string: str) -> bool:
    """The function checks a symbol name"""
    pattern = r'^[0-9A-Z]+$'
    return bool(re.match(pattern, input_string))


async def add_symbol(
    conn: Connection,
    name: str,
    broker_id: int,
) -> int:
    """The functions adds a symbol into DB

    Args:
        conn (Connection): DB connection
        name (str): A symbol name.
        broker_id (int): A broker id.

    Returns:
        int: A new symbol ID
    """    
    # check params
    if not check_symbol_name(name):
        raise ParamsError('Unexpected symbol name. Try to use uppercase name.')

    try:
        await read_broker(conn, broker_id)
    except NotFoundError:
        raise ParamsError(f'Broker with id {broker_id} not found.')

    # insert record
    params = dict(
        name=name,
        broker=broker_id,
    )
    try:
        await conn.execute("""
            INSERT INTO
            symbols (name, broker_id)
            VALUES ($1, $2)
        """, *params.values())
    except UniqueViolationError:
        raise OwnUniqueViolationError

    res = await conn.fetchval('SELECT id FROM symbols ORDER BY id DESC')
    if not res:
        raise ValueError('Insert symbol error')

    return res


async def read_symbol(
    conn: Connection,
    id: int
) -> dict:
    """The functions reads the symbol from DB

    Args:
        conn (Connection): DB connection
        id (int): DB symbol id

    Returns:
        dict: symbol record
    """    
    res = await conn.fetchrow("""
        SELECT * FROM symbols
        WHERE id = $1
    """, id)

    if not res:
        raise NotFoundError

    return dict(res)


async def read_symbols(
    conn: Connection,
) -> list:
    """The functions reads symbols from DB

    Args:
        conn (Connection): DB connection

    Returns:
        list[dict]: list of symbol records
    """    
    res = await conn.fetch("""
        SELECT * FROM symbols
        ORDER BY id
    """)

    return [dict(record) for record in res]


async def update_symbol(
    conn: Connection,
    id: int,
    name: str | None = None,
    broker_id: int | None = None,
) -> None:
    """The functions updates the symbol in DB

    Args:
        conn (Connection): DB connection
        id (int): DB symbol id
        name (str | None): A new name
        broker (int | None): A new broker id
    """    
    if not (name or broker_id):
        raise ValueError('One of params (name, broker_id should be passed for updating.)')

    update_fields = []
    values = []

    values.append(id)

    update_params = {
        "name": name,
        "broker_id": broker_id,
    }

    for key, value in update_params.items():
        if value:
            values.append(value)
            update_fields.append(f"{key} = ${len(values)}")

    update_clause = ", ".join(update_fields)
    query = f"""
        UPDATE symbols
        SET {update_clause}
        WHERE id = $1
    """

    await conn.execute(query, *values)


async def delete_symbol(
    conn: Connection,
    id: int,
) -> None:
    """The function deletes the symbol

    Args:
        conn (Connection): DB connection
        id (int): symbol id
    """    
    await conn.execute("""
        DELETE FROM symbols
        WHERE id = $1;
    """, id)