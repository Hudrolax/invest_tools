from asyncpg import Connection
from .exceptions import NotFoundError, ParamsError


async def add_broker(
    conn: Connection,
    name: str | None = None,
) -> int:
    """The functions adds a broker into DB

    Args:
        conn (Connection): DB connection
        name (str | None, optional): broker name. Defaults to None.

    Returns:
        int: A new broker ID
    """    

    # check exists broker
    res = await conn.fetchval("""
        SELECT id FROM brokers
        WHERE name = $1
    """, name)

    if res:
        raise ParamsError(f'Broker with name "{name}" already exists.')

    await conn.execute("""
        INSERT INTO
        brokers (name)
        VALUES ($1)
    """, name)
    res = await conn.fetchval('SELECT id FROM brokers ORDER BY id DESC')
    if not res:
        raise RuntimeError('Insert broker error')

    return res


async def update_broker(
    conn: Connection,
    id: int,
    name: str,
) -> None:
    """The functions updates a broker in DB

    Args:
        conn (Connection): DB connection
        id (int): broker id
        name (str | None): A new name
    """    
    # check exists broker
    res = await conn.fetchval("""
        SELECT id FROM brokers
        WHERE name = $1 AND id <> $2
    """, name, id)

    if res:
        raise ParamsError(f'Broker with name "{name}" already exists.')

    query = """
        UPDATE brokers
        SET name = $2
        WHERE id = $1
    """

    await conn.execute(query, id, name)


async def read_broker(
    conn: Connection,
    id: int,
) -> dict:
    """The functions reads the broker from DB

    Args:
        conn (Connection): DB connection
        id (int): broker id

    Returns:
        dict: broker record
    """    
    res = await conn.fetchrow("""
        SELECT * FROM brokers
        WHERE id = $1
    """, id)

    if res is None:
        raise NotFoundError(f'Not found broker with id {id}')

    return dict(res)


async def read_brokers(
    conn: Connection,
) -> list:
    """The functions reads all brokers from DB

    Args:
        conn (Connection): DB connection

    Returns:
        list(dict): broker record
    """    
    res = await conn.fetch("""
        SELECT * FROM brokers
        ORDER BY id
    """)

    return [dict(record) for record in res]

async def delete_broker(
    conn: Connection,
    id: int
) -> None:
    """The functions delete a broker from DB

    Args:
        conn (Connection): DB connection
        id (int): broker id
    """    
    await conn.execute("""
        DELETE FROM brokers
        WHERE id = $1
    """, id)