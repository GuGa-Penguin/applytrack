"""Persistence models for tracked job applications."""

from __future__ import annotations

import enum
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    """Return an aware UTC timestamp."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base for every ORM model."""


class Stage(str, enum.Enum):
    """Where an application currently sits in the funnel."""

    SAVED = "saved"
    APPLIED = "applied"
    SCREEN = "screen"
    INTERVIEW = "interview"
    ONSITE = "onsite"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"

    @property
    def is_terminal(self) -> bool:
        """True when no further progress is possible."""
        return self in _TERMINAL_STAGES

    @property
    def is_active(self) -> bool:
        """True while the application is still live."""
        return not self.is_terminal


_TERMINAL_STAGES = frozenset({Stage.REJECTED, Stage.WITHDRAWN, Stage.OFFER})

#: Ordered funnel positions, used to detect forward progress.
STAGE_ORDER: tuple[Stage, ...] = (
    Stage.SAVED,
    Stage.APPLIED,
    Stage.SCREEN,
    Stage.INTERVIEW,
    Stage.ONSITE,
    Stage.OFFER,
)


class Application(Base):
    """A single job application being tracked."""

    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str | None] = mapped_column(String(200))
    source: Mapped[str | None] = mapped_column(String(100))
    url: Mapped[str | None] = mapped_column(String(1000))
    stage: Mapped[Stage] = mapped_column(
        Enum(Stage, native_enum=False), nullable=False, default=Stage.SAVED, index=True
    )
    salary_min: Mapped[int | None] = mapped_column(Integer)
    salary_max: Mapped[int | None] = mapped_column(Integer)
    applied_on: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    fit_score: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    events: Mapped[list["StatusEvent"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        # Same-timestamp events are common; id breaks the tie deterministically.
        order_by="StatusEvent.occurred_at, StatusEvent.id",
    )


class StatusEvent(Base):
    """An immutable record of one stage transition."""

    __tablename__ = "status_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_stage: Mapped[Stage | None] = mapped_column(Enum(Stage, native_enum=False))
    to_stage: Mapped[Stage] = mapped_column(
        Enum(Stage, native_enum=False), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    application: Mapped[Application] = relationship(back_populates="events")
