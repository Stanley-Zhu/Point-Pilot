"""Loyalty programs, such as Chase UR or World of Hyatt. Data rows, not code."""

from sqlalchemy import CheckConstraint, Identity
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Program(Base):
    __tablename__ = "programs"
    __table_args__ = (
        CheckConstraint("kind IN ('bank', 'hotel', 'airline')", name="kind"),
    )

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    kind: Mapped[str]
    currency_name: Mapped[str]
    # Free text shown to the user; the expiry sweep reads accounts.expires_at instead.
    expiry_rule: Mapped[str | None]
