import asyncio
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound, IntegrityError
from fastapi import APIRouter, Depends, HTTPException

from routers import check_token, create_access_token, telegram_bot_authorized
from core.db import get_db
from models.user import UserORM
from models.token import TokenORM


class UserBase(BaseModel):
    username: str | None = None
    telegram_id: int | None = None
    email: str | None = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserCreate(UserLogin):
    telegram_id: int | None = None
    email: str | None = None


class UserUpdate(UserBase):
    pass


class User(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class Token(BaseModel):
    description: str
    token: str


router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "User not found"}},
)


@router.get("/{user_id}/tokens", response_model=list[Token])
async def get_tokens(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    user: UserORM = Depends(check_token)
) -> list[Token]:
    """Returns list of user tokens"""
    if user.id != user_id and not user.superuser: # type: ignore
        raise HTTPException(401, 'Wrong TOKEN')

    return await TokenORM.get_user_tokens(db, user_id) # type: ignore


@router.post("/register", response_model=User)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Add a new user"""
    try:
        user =  await UserORM.create(
            db=db,
            username=user_data.username,
            password=user_data.password,
            telegram_id=user_data.telegram_id,
            email=user_data.email,
        )
        return user
    except ValueError as ex:
        raise HTTPException(422, str(ex))


@router.post("/login")
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    try:
        user = await UserORM.get_by_username(db, user_data.username)
        if user.verify_password(user_data.password):
            token = create_access_token(user_data.model_dump(exclude_unset=True))
            await asyncio.sleep(5)
            return dict(user_id=user.id, token=token)
        else:
            raise HTTPException(401, 'Wrong password')
    except NoResultFound:
        raise HTTPException(404, f'User with username {user_data.username} not found.')


@router.put("/{user_id}", response_model=User)
async def put_user(
    user_id: int,
    data: UserUpdate,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> User:
    if user.id != user_id: # type: ignore
        raise HTTPException(401, 'Wrong TOKEN')

    try:
        return await UserORM.update(db=db, id=user_id, **data.model_dump(exclude_unset=True))
    except NoResultFound:
        raise HTTPException(404, f'User with id {user_id} not found.')
    except (IntegrityError, ValueError) as ex:
        raise HTTPException(422, str(ex))


@router.get("/", response_model=list[User])
async def get_users(
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
):
    if not user.superuser: # type: ignore
        raise HTTPException(401, 'You are not superuser')
    return await UserORM.get_all(db)


@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: int,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> User:
    if user.id != user_id: # type: ignore
        raise HTTPException(401, 'Wrong TOKEN')

    try:
        return await UserORM.get(db, id=user_id)
    except NoResultFound:
        raise HTTPException(404, f'User with id {user_id} not found.')


@router.get("/telegram_bot_api/{user_id}", response_model=User)
async def get_user_telegram_bot_api(
    user_id: int,
    authorized: bool = Depends(telegram_bot_authorized),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        return await UserORM.get(db, id=user_id)
    except NoResultFound:
        raise HTTPException(404, f'User with id {user_id} not found.')


@router.delete("/{user_id}", response_model=bool)
async def del_user(
    user_id: int,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> bool:
    try:
        if user.id != user_id and not user.superuser: # type: ignore
            raise HTTPException(401, 'Wrong TOKEN')
        
        return await UserORM.delete(db, id=user_id)
    except NoResultFound:
        raise HTTPException(404, f'User with id {user_id} not found.')