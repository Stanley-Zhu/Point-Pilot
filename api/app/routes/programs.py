"""The program catalog: list programs and add new ones."""

from fastapi import APIRouter, HTTPException, status
from psycopg import errors
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db import DbSession
from app.models import Program
from app.schemas.program import ProgramCreate, ProgramRead

router = APIRouter(prefix="/programs", tags=["programs"])


@router.get("")
def list_programs(db: DbSession) -> list[ProgramRead]:
    programs = db.scalars(select(Program).order_by(Program.name))
    return [ProgramRead.model_validate(program) for program in programs]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_program(body: ProgramCreate, db: DbSession) -> ProgramRead:
    program = Program(**body.model_dump())
    db.add(program)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # Let the unique constraint decide, rather than checking first: two requests
        # with the same name at once would both pass a check, but only one insert wins.
        orig = exc.orig
        if isinstance(orig, errors.UniqueViolation) and (
            orig.diag.constraint_name == "uq_programs_name"
        ):
            raise HTTPException(
                status.HTTP_409_CONFLICT, f"A program named {body.name!r} already exists."
            ) from exc
        raise
    return ProgramRead.model_validate(program)
