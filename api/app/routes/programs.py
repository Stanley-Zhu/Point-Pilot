"""The program catalog: list programs, add new ones, and delete unused ones."""

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


@router.delete("/{program_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_program(program_id: int, db: DbSession) -> None:
    program = db.get(Program, program_id)
    if program is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Program {program_id} not found.")
    db.delete(program)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # The foreign key decides, as with the name check above: a program with accounts stays.
        orig = exc.orig
        if isinstance(orig, errors.ForeignKeyViolation) and (
            orig.diag.constraint_name == "fk_accounts_program_id_programs"
        ):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Program {program_id} has accounts, so it cannot be deleted.",
            ) from exc
        raise
