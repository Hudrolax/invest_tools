from asyncpg import Connection
from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
from db.db_connection import db
from models.users import (
    add_user,
    update_user,
    read_user,
    read_users,
)
from models.exceptions import NotFoundError, ParamsError
from models.users_api import User, Users, UserWithoutID


router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": " User not found"}},
)


@router.post("/")
async def post_user(
    data: UserWithoutID,
    conn: Connection = Depends(db.get_conn),
) -> User:
    try:
        user_id = await add_user(conn, **dict(data))
        user = await read_user(conn, user_id)
    except ParamsError as ex:
        raise HTTPException(422, ex.message)

    return User(**user)


@router.put("/{user_id}")
async def put_user(
    user_id: int,
    data: UserWithoutID,
    conn: Connection = Depends(db.get_conn),
) -> User:
    try:
        await update_user(conn, id=user_id, **dict(data))
        user = await read_user(conn, id=user_id)
    except ParamsError as ex:
        raise HTTPException(422, ex.message)

    return User(**user)


@router.get("/")
async def get_users(conn: Connection = Depends(db.get_conn)) -> Users:
    users = await read_users(conn)
    return Users(users=users)


@router.get("/{user_id}")
async def get_user(
    user_id: Annotated[int, "User ID"],
    conn: Connection = Depends(db.get_conn),
) -> User:
    try:
        user = await read_user(conn, user_id)
    except NotFoundError as ex:
        raise HTTPException(404, ex.message)

    return User(**user)