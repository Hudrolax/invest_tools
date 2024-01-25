from pydantic import BaseModel, ConfigDict
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
        return await ChecklistORM.create(db=db, user_id=user.id, **data.model_dump())
    except IntegrityError as ex:
        raise HTTPException(422, str(ex))


@router.put("/{checklist_id}", response_model=Checklist)
async def put_checklist(
    checklist_id: int,
    data: ChecklistUpdate,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> Checklist:
    try:
        family_users = await UserORM.get_by_family_group(db, family_group=user.family_group) # type: ignore
        ids_list = [user.id for user in family_users]

        checklist = await ChecklistORM.get(db, id=checklist_id)
        if checklist.user_id not in ids_list: # type: ignore
            raise HTTPException(403, "This cheklist item not from your family group.")
        checklist.checked = data.checked # type: ignore
        await db.flush()
        await db.refresh(checklist)
        return checklist
        
    except NoResultFound:
        raise HTTPException(404, f'Checklist item with id {checklist_id} not found.')
    except (IntegrityError, ValueError) as ex:
        raise HTTPException(422, str(ex))


@router.get("/", response_model=list[Checklist])
async def get_checklist(
    db: AsyncSession = Depends(get_db),
    user: UserORM = Depends(check_token),
):
    family_users = await UserORM.get_by_family_group(db, family_group=user.family_group) # type: ignore
    ids_list = [user.id for user in family_users]
    checklist = await ChecklistORM.get_list(db, user_id=ids_list)

    return checklist


@router.delete("/{checklist_id}", response_model=bool)
async def del_checklist(
    checklist_id: int,
    user: UserORM = Depends(check_token),
    db: AsyncSession = Depends(get_db),
) -> bool:
    try:
        family_users = await UserORM.get_by_family_group(db, family_group=user.family_group) # type: ignore
        ids_list = [user.id for user in family_users]

        checklist = await ChecklistORM.get(db, id=checklist_id)
        if checklist.user_id not in ids_list: # type: ignore
            raise HTTPException(403, "This cheklist item not from your family group.")

        return await ChecklistORM.delete(db, checklist.id) # type: ignore
    except NoResultFound as ex:
        raise HTTPException(404, str(ex))
