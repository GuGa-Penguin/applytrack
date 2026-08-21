"""Request and response schemas for the HTTP API."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import Stage

MAX_DESCRIPTION_CHARS = 60_000


class ApplicationCreate(BaseModel):
    """Payload for registering a new application."""

    company: str = Field(min_length=1, max_length=200)
    role: str = Field(min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    source: str | None = Field(default=None, max_length=100)
    url: str | None = Field(default=None, max_length=1000)
    stage: Stage = Stage.SAVED
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    applied_on: date | None = None
    notes: str | None = None
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_CHARS)

    @model_validator(mode="after")
    def check_salary_range(self) -> "ApplicationCreate":
        """Reject an inverted salary band rather than storing nonsense."""
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError("salary_min must not exceed salary_max")
        return self


class ApplicationUpdate(BaseModel):
    """Partial update. Unset fields are left untouched."""

    company: str | None = Field(default=None, min_length=1, max_length=200)
    role: str | None = Field(default=None, min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    source: str | None = Field(default=None, max_length=100)
    url: str | None = Field(default=None, max_length=1000)
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    applied_on: date | None = None
    notes: str | None = None
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_CHARS)


class StageChange(BaseModel):
    """Payload for moving an application to a new stage."""

    to_stage: Stage
    note: str | None = None


class StatusEventRead(BaseModel):
    """A recorded stage transition."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    from_stage: Stage | None
    to_stage: Stage
    note: str | None
    occurred_at: datetime


class ApplicationRead(BaseModel):
    """An application as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    company: str
    role: str
    location: str | None
    source: str | None
    url: str | None
    stage: Stage
    salary_min: int | None
    salary_max: int | None
    applied_on: date | None
    notes: str | None
    fit_score: int | None
    created_at: datetime
    updated_at: datetime
    events: list[StatusEventRead] = []


class FunnelStats(BaseModel):
    """Aggregate counts across the pipeline."""

    total: int
    active: int
    by_stage: dict[str, int]
    response_rate: float = Field(
        description="Share of applied roles that reached screen or beyond."
    )


class PostingParseRequest(BaseModel):
    """Raw posting text to be parsed by the model."""

    text: str = Field(min_length=1, max_length=MAX_DESCRIPTION_CHARS)
    source: str | None = Field(default=None, max_length=100)
    store_description: bool = True


class ScoreRequest(BaseModel):
    """A candidate profile to assess an application against."""

    profile: str = Field(min_length=1, max_length=20_000)
