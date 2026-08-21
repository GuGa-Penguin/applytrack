"""Score how well a candidate profile matches a posting."""

from __future__ import annotations

from typing import Any

from .client import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    AiRequestError,
    build_client,
    ensure_posting_text,
)
from .schemas import FitAssessment, ParsedPosting

MAX_PROFILE_CHARS = 20_000

SCORING_SYSTEM = """You assess how well a candidate fits a job posting.

Scoring guidance:
- 80-100: meets essentially every requirement.
- 60-79: meets the core requirements with one or two real gaps.
- 40-59: a stretch; several requirements are unmet.
- 0-39: not a realistic fit.

Rules:
- Judge only against evidence in the profile. Absence of evidence is a gap, not
  a strength.
- strengths and gaps must be specific and drawn from the posting's requirements.
- Recommend "apply" at 60 and above, "stretch" between 40 and 59, "skip" below.
- Keep the rationale to two sentences at most."""


def _ensure_profile(profile: str) -> str:
    if not isinstance(profile, str):
        raise TypeError("profile must be a string")
    cleaned = profile.strip()
    if not cleaned:
        raise ValueError("profile is empty")
    if len(cleaned) > MAX_PROFILE_CHARS:
        raise ValueError(f"profile exceeds {MAX_PROFILE_CHARS} characters")
    return cleaned


def assess_fit(
    posting: ParsedPosting | str,
    profile: str,
    *,
    client: Any | None = None,
    model: str = DEFAULT_MODEL,
) -> FitAssessment:
    """Score a candidate profile against a posting."""
    if isinstance(posting, ParsedPosting):
        posting_text = posting.model_dump_json(indent=2)
    else:
        posting_text = ensure_posting_text(posting)

    cleaned_profile = _ensure_profile(profile)
    active_client = client or build_client()

    prompt = (
        f"<posting>\n{posting_text}\n</posting>\n\n"
        f"<candidate_profile>\n{cleaned_profile}\n</candidate_profile>\n\n"
        "Assess the fit."
    )

    try:
        response = active_client.messages.parse(
            model=model,
            max_tokens=DEFAULT_MAX_TOKENS,
            system=SCORING_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            output_format=FitAssessment,
        )
    except Exception as error:
        raise AiRequestError(f"Fit assessment failed: {error}") from error

    parsed = getattr(response, "parsed_output", None)
    if parsed is None:
        raise AiRequestError("Model returned no structured output for the assessment.")
    return parsed
