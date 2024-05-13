from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, func, case, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound, IntegrityError
from fastapi import APIRouter, Depends, HTTPException, Query

from core.db import get_db
from routers import check_token
from models.checklist import ChecklistORM
from models.user import UserORM
from datetime import datetime


class ChecklistBase(BaseModel):
    text: str


class ChecklistCreate(ChecklistBase):
    pass


class ChecklistUpdate(BaseModel):
    checked: bool


class Checklist(ChecklistBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    user: dict
    checked: bool
    date: datetime


router = APIRouter(
    prefix="/checklist",
    tags=["checklist"],
    responses={404: {"description": "Checklist item not found"}},
)


@router.post("/", response_model=Checklist)
async def post_checklist(
    data: ChecklistCreate,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> Checklist:
    try:
        checklist = await ChecklistORM.create(db=db, user_id=user.id, **data.model_dump())
        query = (
            select(
                *ChecklistORM.__table__.c,
                func.json_build_object(
                    'id', UserORM.id.label("user_id"),
                    'name', UserORM.name.label("user_name"),
                ).label("user")
            )
            .select_from(ChecklistORM)
            .join(UserORM, (UserORM.family_group == user.family_group) & (UserORM.id == ChecklistORM.user_id))
            .where(ChecklistORM.id == checklist.id)
        )
        result = (await db.execute(query)).mappings().first()
        if result is None:
            raise HTTPException(404, f'Checklist item with id {
                                checklist.id} not found.')

        return Checklist(**result)
    except IntegrityError as ex:
        raise HTTPException(422, str(ex))


@router.patch("/{checklist_id}", response_model=Checklist)
async def patch_checklist(
    checklist_id: int,
    data: ChecklistUpdate,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> Checklist:
    try:
        query = (
            select(ChecklistORM)
            .select_from(ChecklistORM)
            .join(UserORM, (UserORM.family_group == user.family_group) & (UserORM.id == ChecklistORM.user_id))
            .where(ChecklistORM.id == checklist_id)
        )
        checklist = (await db.execute(query)).scalars().first()
        if checklist is None:  # type: ignore
            raise HTTPException(
                403, "This cheklist item not from your family group or not found.")
        checklist.checked = data.checked  # type: ignore
        await db.flush()
        await db.refresh(checklist)
        query = (
            select(
                *ChecklistORM.__table__.c,
                func.json_build_object(
                    'id', UserORM.id.label("user_id"),
                    'name', UserORM.name.label("user_name"),
                ).label("user")
            )
            .select_from(ChecklistORM)
            .join(UserORM, (UserORM.family_group == user.family_group) & (UserORM.id == ChecklistORM.user_id))
            .where(ChecklistORM.id == checklist_id)
        )
        result = (await db.execute(query)).mappings().first()
        if result is None:
            raise HTTPException(404, f'Checklist item with id {
                                checklist_id} not found.')

        return Checklist(**result)

    except NoResultFound:
        raise HTTPException(404, f'Checklist item with id {
                            checklist_id} not found.')
    except (IntegrityError, ValueError) as ex:
        raise HTTPException(422, str(ex))


@router.get("/", response_model=list[Checklist])
async def get_checklist(
    archive: bool = False,
    db: AsyncSession = Depends(get_db),
    user: UserORM = Depends(check_token),
) -> list[Checklist]:
    query = (
        select(
            *ChecklistORM.__table__.c,
            func.json_build_object(
                'id', UserORM.id.label("user_id"),
                'name', UserORM.name.label("user_name"),
            ).label("user")
        )
        .select_from(ChecklistORM)
        .join(UserORM, (UserORM.family_group == user.family_group) & (UserORM.id == ChecklistORM.user_id))
        .where(ChecklistORM.checked == archive)
        .order_by(desc(ChecklistORM.date))
    )
    result = (await db.execute(query)).mappings().all()
    checklist = [Checklist(**item) for item in result]
    return checklist


@router.delete("/{checklist_id}", response_model=bool)
async def del_checklist(
    checklist_id: int,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> bool:
    try:
        query = (
            select(ChecklistORM)
            .select_from(ChecklistORM)
            .join(UserORM, (UserORM.family_group == user.family_group) & (UserORM.id == ChecklistORM.user_id))
            .where(ChecklistORM.id == checklist_id)
        )
        checklist = (await db.execute(query)).scalars().first()
        if checklist is None:  # type: ignore
            raise HTTPException(
                403, "This cheklist item not from your family group or not found.")

        return await ChecklistORM.delete(db, checklist.id)  # type: ignore
    except NoResultFound as ex:
        raise HTTPException(404, str(ex))
