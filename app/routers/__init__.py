from fastapi import Security, HTTPException, status, Depends
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound
from datetime import datetime, timedelta
from jose import jwt, JWTError

from core.db import get_db
from core.config import SECRET, TELEGRAM_BOT_SECRET
from models.user import UserORM


api_key_header = APIKeyHeader(name="TOKEN", auto_error=False)
telegram_bot_secret = APIKeyHeader(name="TBOT-SECRET", auto_error=False)
telegram_bot_user_id = APIKeyHeader(name="TELEGRAM-ID", auto_error=False)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 43200


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> str:
    """Verify JWT token

    Args:
        token (str): token

    Returns:
        str: username
    """    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        username: str = payload.get("username") # type: ignore
        if username is None:
            raise credentials_exception
        expiration = payload.get("exp")
        if expiration is not None and datetime.utcfromtimestamp(expiration) < datetime.utcnow():
            raise HTTPException(status_code=401, detail="Token is expired")
        return username  # или полный payload, если нужно
    except (JWTError, AttributeError) as ex:
        raise credentials_exception


# authentication
async def check_token(
    db: AsyncSession = Depends(get_db),
    telegram_bot_secret: str = Security(telegram_bot_secret),
    telegram_id: str = Security(telegram_bot_user_id),
    header_token: str = Security(api_key_header),
) -> UserORM:
    """Check token in the Headers and return a user or raise 401 exception"""
    try:
        if telegram_id and telegram_bot_secret == TELEGRAM_BOT_SECRET:
            return await UserORM.get_by_telegram_id(db, int(telegram_id))

        else:
            try:
                return await UserORM.get_by_token(db, header_token)
            except NoResultFound:
                username = verify_token(header_token)
                return await UserORM.get_by_username(db, username)
    except:
        raise HTTPException(401)


# authentication telegram_api
async def telegram_bot_authorized(
    telegram_bot_secret: str = Security(telegram_bot_secret),
) -> bool:
    """Check token in the Headers and return a user or raise 401 exception"""
    if telegram_bot_secret == TELEGRAM_BOT_SECRET:
        return True
    raise HTTPException(401)