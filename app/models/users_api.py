from pydantic import BaseModel
from typing import Annotated


class UserWithoutID(BaseModel):
    """A user instance without id"""
    name: Annotated[str, "Username"]
    telegram_id: Annotated[int | None, "user's telegram id"] = None
    email: Annotated[str | None, "user's email"] = None


class User(UserWithoutID):
    """A user instance with ID"""
    id: Annotated[int, "User ID"]


class Users(BaseModel):
    """List of users"""
    users: Annotated[list[User], "List of user instances"]