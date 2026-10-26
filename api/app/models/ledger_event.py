"""The append-only ledger. A balance is the sum of an account's events."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Identity, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LedgerEvent(Base):
    __tablename__ = "ledger_events"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('earn', 'burn', 'transfer_in', 'transfer_out', 'expire', 'adjust', 'reversal')",
            name="kind",
        ),
        CheckConstraint(
            "source IN ('manual', 'csv', 'awardwallet', 'reconciliation')",
            name="source",
        ),
        CheckConstraint(
            "(kind IN ('earn', 'transfer_in') AND points > 0)"
            " OR (kind IN ('burn', 'transfer_out', 'expire') AND points < 0)"
            " OR (kind IN ('adjust', 'reversal') AND points <> 0)",
            name="sign_matches_kind",
        ),
        # A transfer is two events, transfer_out and transfer_in, sharing one group id.
        CheckConstraint(
            "kind NOT IN ('transfer_in', 'transfer_out') OR transfer_group_id IS NOT NULL",
            name="transfer_has_group",
        ),
        # A reversal must point at the event it undoes, and only a reversal may.
        CheckConstraint(
            "(kind = 'reversal') = (reverses_event_id IS NOT NULL)",
            name="reversal_has_target",
        ),
        # Re-syncs and re-imports are idempotent. Postgres treats NULLs as distinct,
        # so events without an external_ref never conflict.
        UniqueConstraint("source", "external_ref"),
    )

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    kind: Mapped[str]
    points: Mapped[int]
    occurred_at: Mapped[datetime]
    recorded_at: Mapped[datetime] = mapped_column(server_default=func.now())
    source: Mapped[str]
    external_ref: Mapped[str | None]
    note: Mapped[str | None]
    transfer_group_id: Mapped[uuid.UUID | None]
    # UNIQUE, so an event can be undone only once.
    reverses_event_id: Mapped[int | None] = mapped_column(
        ForeignKey("ledger_events.id"), unique=True
    )
    # Set on reconciliation adjusts: the snapshot that revealed the gap.
    snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("balance_snapshots.id"))
