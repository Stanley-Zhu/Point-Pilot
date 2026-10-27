"""account balances view, programs.kind allows other

Revision ID: f7c0b1f3c2d4
Revises: 14cb4399e069
Create Date: 2026-10-26 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f7c0b1f3c2d4'
down_revision: Union[str, Sequence[str], None] = '14cb4399e069'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Hand-written: autogenerate does not detect views.
    # A plain view, so a balance is always the current sum of the ledger, with no refresh step.
    # LEFT JOIN so an account with no events yet shows 0 instead of being missing.
    # SUM of BIGINT returns NUMERIC in Postgres, so cast back to keep points a BIGINT.
    op.execute(
        """
        CREATE VIEW account_balances AS
        SELECT
            accounts.id AS account_id,
            COALESCE(SUM(ledger_events.points), 0)::BIGINT AS points
        FROM accounts
        LEFT JOIN ledger_events ON ledger_events.account_id = accounts.id
        GROUP BY accounts.id
        """
    )
    # A view has its own grants. Read-only, like everything derived from the ledger.
    op.execute("GRANT SELECT ON account_balances TO pointpilot_admin")

    # Postgres cannot edit a CHECK expression in place, so drop it and add it back.
    # op.f() marks the name as final, so the naming convention is not applied twice.
    op.drop_constraint(op.f('ck_programs_kind'), 'programs', type_='check')
    op.create_check_constraint(
        op.f('ck_programs_kind'), 'programs', "kind IN ('bank', 'hotel', 'airline', 'other')"
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Fails if any program has kind 'other'; change or remove those rows first.
    op.drop_constraint(op.f('ck_programs_kind'), 'programs', type_='check')
    op.create_check_constraint(
        op.f('ck_programs_kind'), 'programs', "kind IN ('bank', 'hotel', 'airline')"
    )
    op.execute("DROP VIEW account_balances")
