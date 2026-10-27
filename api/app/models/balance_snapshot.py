"""Point-in-time totals from a parsed program email or a manual check-in."""

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Identity
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BalanceSnapshot(Base):
    __tablename__ = "balance_snapshots"
    __table_args__ = (
        CheckConstraint("source IN ('manual', 'email')", name="source"),
        # point balances can't be negative for a snapshot
        CheckConstraint("points >= 0", name="points_not_negative"),
    )

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    points: Mapped[int]
    # For email, the date the email says the balance was true, not when the email arrived.
    balance_as_of: Mapped[datetime]
    source: Mapped[str]
    external_ref: Mapped[str | None]
