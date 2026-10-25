"""SQLAlchemy models. Import every model module here so Base.metadata sees all tables."""

from app.models.base import Base

__all__ = ["Base"]
