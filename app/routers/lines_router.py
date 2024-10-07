from pydantic import BaseModel, validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import NoResultFound, IntegrityError
from datetime import datetime
from decimal import Decimal

from routers import check_token
from core.db import get_db
from models.lines import LineORM, LINE_TYPES
from models.user import UserORM
from models.symbol import SymbolORM
from models.symbol import BrokerORM
from . import format_decimal


class LineBase(BaseModel):
    line_type: str
    x0: int
    y0: str
    x1: int
    y1: str
    label: str | None
    color: str
    width: str
    created_at: int

    @validator("x0", "x1", "created_at", pre=True, always=True)
    def parse_datetime(cls, value):
        if isinstance(value, datetime):
            return int(value.timestamp())
        else:
            raise TypeError(f"{value} is not datetime")

    @validator("y0", "y1", "width", pre=True)
    def format_decimal_fields(cls, value):
        if value is not None:
            return format_decimal(value)
        return value


class LineInstance(LineBase):
    id: int


class LineCreate(BaseModel):
    broker_name: str
    symbol_name: str
    line_type: str
    x0: int
    y0: str
    x1: int
    y1: str
    label: str | None = None
    color: str = "white"
    width: int = 1

    @validator("line_type", pre=True, always=True)
    def parse_line_type(cls, value):
        if value not in LINE_TYPES:
            raise ValueError(f"line_type must be in {LINE_TYPES}")

        return value


class LineUpdate(BaseModel):
    x0: int
    y0: str
    x1: int
    y1: str
    color: str
    width: int
    label: str | None = None


router = APIRouter(
    prefix="/lines",
    tags=["lines"],
    responses={404: {"description": "lines not found"}},
)


@router.post("/", response_model=bool)
async def post_line(
    data: LineCreate,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> bool:
    try:
        await LineORM.create(
            db=db,
            user_id=user.id,
            symbol_name=data.symbol_name,
            broker_name=data.broker_name,
            line_type=data.line_type,
            x0=datetime.fromtimestamp(data.x0),
            y0=Decimal(data.y0),
            x1=datetime.fromtimestamp(data.x1),
            y1=Decimal(data.y1),
            color=data.color,
            width=int(data.width) if data.width else None,
        )

        return True

    except (IntegrityError, NoResultFound, ValueError) as ex:
        raise HTTPException(422, str(ex))


@router.get("/{broker_name}/{symbol_name}", response_model=list[dict])
async def get_lines(
    broker_name: str,
    symbol_name: str,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    query = (
        select(
            LineORM.id,
            LineORM.line_type,
            LineORM.x0,
            LineORM.y0,
            LineORM.x1,
            LineORM.y1,
            LineORM.label,
            LineORM.color,
            LineORM.width,
            LineORM.created_at,
        )
        .select_from(LineORM)
        .join(BrokerORM, BrokerORM.name == broker_name)
        .join(
            SymbolORM,
            (SymbolORM.name == symbol_name)
            & (SymbolORM.broker_id == BrokerORM.id),
        )
        .where(LineORM.user_id == user.id)
    )

    result = (await db.execute(query)).mappings().all()

    return [
        LineInstance(**line).model_dump(exclude_none=True) for line in result
    ]


@router.put("/{line_id}", response_model=bool)
async def update_line(
    line_id: int,
    data: LineUpdate,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> bool:
    try:
        line = await LineORM.get(db, line_id)
        if line.user_id != user.id:  # type: ignore
            raise HTTPException(401, "Wrong TOKEN")

        await LineORM.update(
            db=db, id=line_id, **data.model_dump(exclude_unset=True)
        )
        return True
    except NoResultFound:
        raise HTTPException(404, f"Line with id {line_id} not found.")
    except (IntegrityError, ValueError) as ex:
        raise HTTPException(422, str(ex))


@router.delete("/{line_id}", response_model=bool)
async def del_line(
    line_id: int,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> bool:
    try:
        line = await LineORM.get(db, id=line_id)
        if line.user_id != user.id:  # type: ignore
            raise HTTPException(401, "Wrong TOKEN")

        return await LineORM.delete(db, id=line_id)
    except NoResultFound:
        raise HTTPException(404, f"Line with id {line_id} not found.")

    except Exception as ex:
        raise HTTPException(500, str(ex))
