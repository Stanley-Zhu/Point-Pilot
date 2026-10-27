"""The ledger core tables, constraints, and grants, exercised as pointpilot_app."""

import uuid
from datetime import UTC, datetime

import pytest
from psycopg import errors
from sqlalchemy import Executable, delete, text, update
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from app.models import Account, BalanceSnapshot, LedgerEvent, Program


@pytest.fixture
def account(db: Session) -> Account:
    program = Program(name="Chase Ultimate Rewards", kind="bank", currency_name="UR points")
    db.add(program)
    db.flush()
    account = Account(program_id=program.id, member_ref="1234")
    db.add(account)
    db.flush()
    return account


def make_event(account: Account, **overrides: object) -> LedgerEvent:
    """A valid earn event; tests override only the fields they are checking."""
    fields: dict[str, object] = {
        "kind": "earn",
        "points": 1000,
        "occurred_at": datetime.now(UTC),
        "source": "manual",
        **overrides,
    }
    return LedgerEvent(account_id=account.id, **fields)


def assert_rejected(db: Session, row: object, constraint: str) -> None:
    """Insert the row and expect Postgres to reject it with the named constraint."""
    with pytest.raises(IntegrityError) as exc_info:
        # A savepoint, so the failed insert rolls back without losing the test's earlier rows.
        with db.begin_nested():
            db.add(row)
            db.flush()
    # orig is the driver's own exception; narrow it so .diag is known to exist.
    orig = exc_info.value.orig
    assert isinstance(orig, errors.IntegrityError)
    assert orig.diag.constraint_name == constraint


def test_app_role_can_insert_a_program(db: Session) -> None:
    program = Program(name="Chase Ultimate Rewards", kind="bank", currency_name="UR points")
    db.add(program)
    db.flush()

    assert program.id is not None


def test_program_kind_must_be_known(db: Session) -> None:
    program = Program(name="Cruise Club", kind="cruise", currency_name="points")
    assert_rejected(db, program, "ck_programs_kind")


def test_member_ref_keeps_only_last_4(db: Session, account: Account) -> None:
    full_number = Account(program_id=account.program_id, member_ref="123456789")
    assert_rejected(db, full_number, "ck_accounts_member_ref_last_4")


def test_snapshot_points_cannot_be_negative(db: Session, account: Account) -> None:
    snapshot = BalanceSnapshot(
        account_id=account.id, points=-1, balance_as_of=datetime.now(UTC), source="manual"
    )
    assert_rejected(db, snapshot, "ck_balance_snapshots_points_not_negative")


def test_event_kind_must_be_known(db: Session, account: Account) -> None:
    assert_rejected(db, make_event(account, kind="gift"), "ck_ledger_events_kind")


@pytest.mark.parametrize(
    ("kind", "points"),
    [
        ("earn", 500),
        ("transfer_in", 500),
        ("burn", -500),
        ("transfer_out", -500),
        ("expire", -500),
        ("adjust", 500),
        ("adjust", -500),
    ],
)
def test_sign_matches_kind_accepts(db: Session, account: Account, kind: str, points: int) -> None:
    group = uuid.uuid4() if kind.startswith("transfer") else None
    db.add(make_event(account, kind=kind, points=points, transfer_group_id=group))
    db.flush()


@pytest.mark.parametrize(
    ("kind", "points"),
    [
        ("earn", -500),
        ("transfer_in", -500),
        ("burn", 500),
        ("transfer_out", 500),
        ("expire", 500),
        ("adjust", 0),
    ],
)
def test_sign_matches_kind_rejects(db: Session, account: Account, kind: str, points: int) -> None:
    # Transfers get a group id so the sign check is the only rule being broken.
    group = uuid.uuid4() if kind.startswith("transfer") else None
    event = make_event(account, kind=kind, points=points, transfer_group_id=group)
    assert_rejected(db, event, "ck_ledger_events_sign_matches_kind")


def test_transfer_needs_a_group(db: Session, account: Account) -> None:
    event = make_event(account, kind="transfer_out", points=-500)
    assert_rejected(db, event, "ck_ledger_events_transfer_has_group")


def test_reversal_needs_a_target(db: Session, account: Account) -> None:
    event = make_event(account, kind="reversal", points=-1000)
    assert_rejected(db, event, "ck_ledger_events_reversal_has_target")


def test_only_a_reversal_may_have_a_target(db: Session, account: Account) -> None:
    original = make_event(account)
    db.add(original)
    db.flush()

    event = make_event(account, reverses_event_id=original.id)
    assert_rejected(db, event, "ck_ledger_events_reversal_has_target")


def test_an_event_can_be_reversed_only_once(db: Session, account: Account) -> None:
    original = make_event(account)
    db.add(original)
    db.flush()
    db.add(make_event(account, kind="reversal", points=-1000, reverses_event_id=original.id))
    db.flush()

    second = make_event(account, kind="reversal", points=-1000, reverses_event_id=original.id)
    assert_rejected(db, second, "uq_ledger_events_reverses_event_id")


def test_reimporting_the_same_row_is_rejected(db: Session, account: Account) -> None:
    db.add(make_event(account, source="csv", external_ref="row-1"))
    db.flush()

    duplicate = make_event(account, source="csv", external_ref="row-1")
    assert_rejected(db, duplicate, "uq_ledger_events_source_external_ref")


def test_events_without_external_ref_never_conflict(db: Session, account: Account) -> None:
    db.add_all([make_event(account), make_event(account)])
    db.flush()


@pytest.mark.parametrize(
    "statement",
    [
        update(LedgerEvent).values(note="edited"),
        delete(LedgerEvent),
        update(BalanceSnapshot).values(points=0),
        delete(BalanceSnapshot),
    ],
    ids=["update ledger_events", "delete ledger_events", "update snapshots", "delete snapshots"],
)
def test_app_role_cannot_change_history(db: Session, statement: Executable) -> None:
    # Postgres checks privileges before it looks for rows, so no rows are needed.
    with pytest.raises(ProgrammingError) as exc_info:
        with db.begin_nested():
            db.execute(statement)
    assert isinstance(exc_info.value.orig, errors.InsufficientPrivilege)


def balance_of(db: Session, account: Account) -> int:
    """The account's row in the account_balances view, read as pointpilot_app."""
    db.flush()
    query = text("SELECT points FROM account_balances WHERE account_id = :account_id")
    return db.execute(query, {"account_id": account.id}).scalar_one()


def test_balance_of_a_new_account_is_zero(db: Session, account: Account) -> None:
    # LEFT JOIN: an account with no events still has a row.
    assert balance_of(db, account) == 0


def test_balance_is_the_sum_of_events(db: Session, account: Account) -> None:
    db.add_all(
        [
            make_event(account, kind="earn", points=1000),
            make_event(account, kind="burn", points=-300),
            make_event(account, kind="adjust", points=50),
        ]
    )

    balance = balance_of(db, account)

    assert balance == 750
    # The ::BIGINT cast: without it, SUM returns NUMERIC and this would be a Decimal.
    assert type(balance) is int


def test_reversal_cancels_its_event(db: Session, account: Account) -> None:
    original = make_event(account, points=1000)
    db.add(original)
    db.flush()
    db.add(make_event(account, kind="reversal", points=-1000, reverses_event_id=original.id))

    assert balance_of(db, account) == 0


def test_transfer_moves_points_between_accounts(db: Session, account: Account) -> None:
    other = Account(program_id=account.program_id, member_ref="5678")
    db.add(other)
    db.flush()
    group = uuid.uuid4()
    db.add_all(
        [
            make_event(account, kind="earn", points=1000),
            make_event(account, kind="transfer_out", points=-400, transfer_group_id=group),
            make_event(other, kind="transfer_in", points=400, transfer_group_id=group),
        ]
    )

    assert balance_of(db, account) == 600
    assert balance_of(db, other) == 400
