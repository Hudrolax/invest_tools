import asyncio
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound, IntegrityError
from fastapi import APIRouter, Depends, HTTPException

from routers import check_token, create_access_token, telegram_bot_authorized
from core.db import get_db
from models.user import UserORM
from models.token import TokenORM
from core.config import OPENAI_API_KEY


class UserBase(BaseModel):
    username: str | None = None
    telegram_id: int | None = None
    email: str | None = None
    name: str | None = None
    family_group: str | None = None
    family_leader: int | None = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserData(BaseModel):
    user_id: int
    token: str
    openai_api_key: str


class UserCreate(UserLogin):
    name: str
    telegram_id: int | None = None
    email: str | None = None


class UserUpdate(UserBase):
    pass


class UpdatePassword(BaseModel):
    password: str


class User(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class Token(BaseModel):
    description: str
    token: str

class OpenAIToken(BaseModel):
    key: str

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
    if user.id != user_id and not user.superuser:  # type: ignore
        raise HTTPException(401, 'Wrong TOKEN')

    return await TokenORM.get_user_tokens(db, user_id)  # type: ignore


@router.post("/register", response_model=User)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Add a new user"""
    try:
        user = await UserORM.create(
            db=db,
            username=user_data.username,
            password=user_data.password,
            telegram_id=user_data.telegram_id,
            email=user_data.email,
            name=user_data.name
        )
        return user
    except ValueError as ex:
        raise HTTPException(422, str(ex))


@router.put("/recover/{user_id}", response_model=User)
async def recover(
    user_id: int,
    data: UpdatePassword,
    db: AsyncSession = Depends(get_db),
    user: UserORM = Depends(check_token),
):
    """recover user password"""
    try:
        if user_id != user.id and not user.superuser: # type: ignore
            raise HTTPException(422, 'Wrong credentials')


        user = await UserORM.get(db=db, id=user.id) # type: ignore
        if user:
            await user.update_password(db, data.password)
        else:
            raise HTTPException(404, f'User with id {user.id} not found.') # type: ignore
        return user
    except ValueError as ex:
        raise HTTPException(422, str(ex))


@router.post("/login", response_model=UserData)
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    try:
        user = await UserORM.get_by_username(db, user_data.username)
        if user.verify_password(user_data.password):
            token = create_access_token(
                user_data.model_dump(exclude_unset=True))
            return UserData(
                    user_id=int(user.id),  # type: ignore
                    token=token,
                    openai_api_key=OPENAI_API_KEY,
                )
        else:
            raise HTTPException(401, 'Wrong password')
    except NoResultFound:
        raise HTTPException(404, f'User with username {
                            user_data.username} not found.')


@router.put("/{user_id}", response_model=User)
async def put_user(
    user_id: int,
    data: UserUpdate,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> User:
    if user.id != user_id:  # type: ignore
        raise HTTPException(401, 'Wrong TOKEN')

    try:
        return await UserORM.update(db=db, id=user_id, **data.model_dump(exclude_unset=True))
    except NoResultFound:
        raise HTTPException(404, f'User with id {user_id} not found.')
    except (IntegrityError, ValueError) as ex:
        raise HTTPException(422, str(ex))


@router.get("/", response_model=list[User])
async def get_users(
    family_group: str | None = None,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
):
    if family_group:
        if user.family_group == family_group:  # type: ignore
            return await UserORM.get_by_family_group(db, family_group)
        else:
            raise HTTPException(422, "It's not your family group")

    if not user.superuser:  # type: ignore
        raise HTTPException(401, 'You are not superuser')
    return await UserORM.get_all(db)


@router.get("/user_info", response_model=User)
async def get_user_by_token(
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        return await UserORM.get(db, id=user.id)
    except NoResultFound:
        raise HTTPException(404, f'User with id {user.id} not found.')


@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: int,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> User:
    if user.id != user_id:  # type: ignore
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
        if user.id != user_id and not user.superuser:  # type: ignore
            raise HTTPException(401, 'Wrong TOKEN')

        return await UserORM.delete(db, id=user_id)
    except NoResultFound:
        raise HTTPException(404, f'User with id {user_id} not found.')


# @router.get("/{user_id}/openai_key", response_model=OpenAIToken)
# async def get_openai_token(
#     user_id: int,
#     user: UserORM = Depends(check_token)
# ) -> OpenAIToken:
#     """Returns OpenAI token"""
#     if user.id != user_id and not user.superuser:  # type: ignore
#         raise HTTPException(401, 'Wrong TOKEN')

#     return OpenAIToken(key=OPENAI_API_KEY)
