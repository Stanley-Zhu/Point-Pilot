"""Loyalty program request and response shapes."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Mirrors ck_programs_kind, so a bad kind is a clear 422 instead of a database error.
ProgramKind = Literal["bank", "hotel", "airline", "other"]


class ProgramCreate(BaseModel):
    name: str = Field(min_length=1)
    kind: ProgramKind
    currency_name: str = Field(min_length=1)
    expiry_rule: str | None = None


class ProgramRead(ProgramCreate):
    # Built from a Program row, not only from a dict.
    model_config = ConfigDict(from_attributes=True)

    id: int
