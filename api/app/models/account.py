"""One row per loyalty account. Single-user for now, so there is no user_id yet."""

from datetime import date

from sqlalchemy import CheckConstraint, ForeignKey, Identity
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'closed')", name="status"),
        # Only the last 4 characters, so a full member number is never stored.
        CheckConstraint("char_length(member_ref) <= 4", name="member_ref_last_4"),
    )

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id"), index=True)
    member_ref: Mapped[str | None]
    status: Mapped[str] = mapped_column(server_default="active")
    expires_at: Mapped[date | None]
