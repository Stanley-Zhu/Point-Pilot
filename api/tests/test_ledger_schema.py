"""The ledger core tables, constraints, and grants, exercised as pointpilot_app."""

from sqlalchemy.orm import Session

from app.models import Program


def test_app_role_can_insert_a_program(db: Session) -> None:
    program = Program(name="Chase Ultimate Rewards", kind="bank", currency_name="UR points")
    db.add(program)
    db.flush()

    assert program.id is not None
