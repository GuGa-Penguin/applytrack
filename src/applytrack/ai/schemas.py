"""Structured shapes the model is asked to return."""

from __future__ import annotations

import enum

from pydantic import BaseModel, Field


class RemotePolicy(str, enum.Enum):
    """How much on-site presence the posting requires."""

    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    UNSPECIFIED = "unspecified"


class Recommendation(str, enum.Enum):
    """What the candidate should do about this posting."""

    APPLY = "apply"
    STRETCH = "stretch"
    SKIP = "skip"


class ParsedPosting(BaseModel):
    """Fields extracted from a raw job posting."""

    company: str = Field(description="Hiring company. Empty string if not stated.")
    role: str = Field(description="Job title as written in the posting.")
    location: str = Field(default="", description="Primary location, or empty.")
    remote_policy: RemotePolicy = RemotePolicy.UNSPECIFIED
    seniority: str = Field(default="", description="e.g. junior, senior, staff.")
    employment_type: str = Field(default="", description="e.g. full-time, contract.")
    salary_min: int | None = Field(default=None, description="Annual minimum, or null.")
    salary_max: int | None = Field(default=None, description="Annual maximum, or null.")
    currency: str = Field(default="", description="ISO code such as CAD or USD.")
    required_skills: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    summary: str = Field(default="", description="Two sentences at most.")


class FitAssessment(BaseModel):
    """A judgement of how well a candidate matches a posting."""

    score: int = Field(ge=0, le=100, description="Overall fit, 0 to 100.")
    recommendation: Recommendation
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    rationale: str = Field(default="", description="Two sentences at most.")
