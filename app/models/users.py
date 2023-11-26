from asyncpg import Connection
from .exceptions import ParamsError, NotFoundError
import re


def is_valid_email(email) -> bool:
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.search(email_pattern, email))


async def add_user(
    conn: Connection,
    name: str | None = None,
    telegram_id: int | None = None,
    email: str | None = None
) -> int:
    """The functions adds a user into DB

    Args:
        conn (Connection): DB connection
        name (str | None, optional): user name. Defaults to None.
        telegram_id (int | None, optional): telegram id. Defaults to None.
        email (str | None, optional): email. Defaults to None.

    Returns:
        int: A new user ID
    """    
    if not email and not telegram_id:
        raise ParamsError('telegram_id or email should be passed.')

    if email and not is_valid_email(email):
        raise ParamsError('Wrong email format.')

    params = dict(
        name=name,
        telegram_id=telegram_id,
        email=email,
    )
    await conn.execute("""
        INSERT INTO
        users (name, telegram_id, email)
        VALUES ($1, $2, $3)
    """, *params.values())
    res = await conn.fetchval('SELECT id FROM users ORDER BY id DESC')
    if not res:
        raise ValueError('Insert user error')

    return res

async def read_user(
    conn: Connection,
    id: int
) -> dict:
    """The functions reads the user from DB

    Args:
        conn (Connection): DB connection
        id (int): DB user id

    Returns:
        dict: user record
    """    
    res = await conn.fetchrow("""
        SELECT * FROM users
        WHERE id = $1
    """, id)
    if not res:
        raise NotFoundError(f'A user with id {id} not found.')

    return res


async def read_users(
    conn: Connection,
) -> list:
    """The functions reads users from DB

    Args:
        conn (Connection): DB connection

    Returns:
        list[dict]: list of user records
    """    
    res = await conn.fetch("""
        SELECT * FROM users
        ORDER BY id
    """)

    return [dict(record) for record in res]


async def update_user(
    conn: Connection,
    id: int,
    name: str | None = None,
    telegram_id: int | None = None,
    email: str | None = None,
) -> None:
    """The functions updates the user in DB

    Args:
        conn (Connection): DB connection
        id (int): DB user id
        name (str | None): A new name
        telegram_id (int | None): A new telegram id
        email (str | None): A new telegram id
    """    
    if not (name or telegram_id or email):
        raise ValueError('One of params (name, telegram_id, email should be passed for updating.)')

    if email and not is_valid_email(email):
        raise ParamsError('Wrong email format.')

    update_fields = []
    values = []

    values.append(id)

    update_params = {
        "name": name,
        "telegram_id": telegram_id,
        "email": email
    }

    for key, value in update_params.items():
        if value:
            values.append(value)
            update_fields.append(f"{key} = ${len(values)}")

    update_clause = ", ".join(update_fields)
    query = f"""
        UPDATE users
        SET {update_clause}
        WHERE id = $1
    """

    await conn.execute(query, *values)