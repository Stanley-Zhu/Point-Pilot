"""admin can delete programs

Revision ID: 3a9e5d71c0b2
Revises: f7c0b1f3c2d4
Create Date: 2026-10-26 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '3a9e5d71c0b2'
down_revision: Union[str, Sequence[str], None] = 'f7c0b1f3c2d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # For DELETE /programs/{id}, to fix mistakes. A program with accounts still cannot be
    # deleted: fk_accounts_program_id_programs refuses, so no history is ever orphaned.
    # Accounts, snapshots, and ledger events stay undeletable.
    op.execute("GRANT DELETE ON programs TO pointpilot_admin")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("REVOKE DELETE ON programs FROM pointpilot_admin")
