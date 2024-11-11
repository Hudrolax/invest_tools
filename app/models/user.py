from sqlalchemy import Column, Integer, BIGINT, BOOLEAN, String, select, asc, ForeignKey
from sqlalchemy.exc import NoResultFound, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship
from typing import Self, Sequence
from passlib.context import CryptContext

from .base_object import BaseDBObject
from models.token import TokenORM

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserORM(BaseDBObject):
    __tablename__ = "users"  # type: ignore
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True, default='user')
    hashed_password = Column(String)
    telegram_id = Column(BIGINT, index=True)
    email = Column(String, index=True)
    superuser = Column(BOOLEAN, nullable=False, default=False)
    family_group = Column(String)
    family_leader = Column(Integer, ForeignKey('users.id'))
    last_symbol_id = Column(Integer, ForeignKey("symbols.id", ondelete="CASCADE"), nullable=True) # Last choosed symbol on the chart

    alerts = relationship('AlertORM', back_populates='user', cascade="all, delete")
    tokens = relationship('TokenORM', back_populates='user', cascade="all, delete")
    wallet_transactions = relationship('WalletTransactionORM', back_populates='user', cascade="all, delete")
    user_wallets = relationship('UserWalletsORM', back_populates='user', cascade="all, delete")
    user_exin_items = relationship('UserExInItemORM', back_populates='user', cascade="all, delete")
    checklist = relationship('ChecklistORM', back_populates='user', cascade="all, delete")
    lines = relationship('LineORM', back_populates='user', cascade="all, delete")
    orders = relationship('OrderORM', back_populates='user', cascade="all, delete")
    positions = relationship('PositionORM', back_populates='user', cascade="all, delete")
    chart_settings = relationship('ChartSettingsORM', back_populates='user', cascade="all, delete")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def verify_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.hashed_password) # type: ignore

    def set_password(self, password: str) -> None:
        self.hashed_password = pwd_context.hash(password)
    
    async def update_password(self, db, password: str) -> bool:
        self.hashed_password = pwd_context.hash(password)
        await db.flush()
        return True

    @classmethod
    async def validate(cls, user: 'UserORM.instance', db: AsyncSession) -> None:
        if not (user.telegram_id or user.email):
            raise ValueError("Either telegram_id or email must be set.")
        
        if user.email:
            user_by_email = await db.execute(select(UserORM).where(
                UserORM.email == user.email,
                UserORM.id != user.id
            ))
            if user_by_email.scalars().first() is not None:
                raise ValueError("User with this email already exists.")

        if user.telegram_id:
            user_by_telegram_id = await db.execute(select(UserORM).where(
                UserORM.telegram_id == user.telegram_id,
                UserORM.id != user.id
            ))
            if user_by_telegram_id.scalars().first() is not None:
                raise ValueError("User with this telegram_id already exists.")

    @classmethod
    async def create(cls, db: AsyncSession, **kwargs) -> Self:
        try:
            password = kwargs.pop('password')

            user_by_username = await db.execute(select(UserORM).where(
                UserORM.username == kwargs['username']
            ))
            if user_by_username.scalars().first() is not None:
                raise ValueError("User with this username already exists.")

            obj = cls(**kwargs)
            # can't create superuser
            obj.superuser = False

            obj.set_password(password)
            db.add(obj)
            await db.flush()
            await cls.validate(obj, db)
        except (IntegrityError, ValueError):
            await db.rollback()
            raise
        return obj

    @classmethod
    async def get_all(cls, db: AsyncSession) -> Sequence[Self]:
        result = await db.execute(select(cls).order_by(asc(cls.id)))  # сортировка по возрастанию id
        return result.scalars().all()
    
    @classmethod
    async def get_by_family_group(cls, db: AsyncSession, family_group: str) -> Sequence[Self]:
        result = await db.execute(
            select(cls).where(cls.family_group == family_group).order_by(asc(cls.id))
        )  # сортировка по возрастанию id, фильтрация по family_group
        return result.scalars().all()

    @classmethod
    async def get_by_token(cls, db: AsyncSession, token: str) -> Self:
        result = (await db.scalars(select(cls).join(cls.tokens).where(TokenORM.token == token))).first()
        if not result:
            raise NoResultFound
        return result
    @classmethod
    async def get_by_username(cls, db: AsyncSession, username: str) -> Self:
        result = (await db.scalars(select(cls).where(cls.username == username))).first()
        if not result:
            raise NoResultFound
        return result

    @classmethod
    async def get_by_telegram_id(cls, db: AsyncSession, telegram_id: int) -> Self:
        result = (await db.scalars(select(cls).where(cls.telegram_id == telegram_id))).first()
        if not result:
            raise NoResultFound
        return result
