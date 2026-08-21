"""Turn a raw job posting into structured fields using Claude."""

from __future__ import annotations

from typing import Any

from ..schemas import ApplicationCreate
from .client import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    AiRequestError,
    build_client,
    ensure_posting_text,
)
from .schemas import ParsedPosting

EXTRACTION_SYSTEM = """You extract structured data from job postings.

Rules:
- Copy values from the posting. Never invent a company, title, or salary.
- If a field is not stated, leave it empty or null rather than guessing.
- Salary must be an annual figure in whole units. Convert hourly rates only when
  the posting states expected hours; otherwise leave salary null.
- required_skills are those the posting frames as necessary; nice_to_have are
  those framed as preferred or bonus.
- Keep the summary to two sentences at most."""


def parse_posting(
    text: str,
    *,
    client: Any | None = None,
    model: str = DEFAULT_MODEL,
) -> ParsedPosting:
    """Extract structured fields from a raw job posting."""
    cleaned = ensure_posting_text(text)
    active_client = client or build_client()

    try:
        response = active_client.messages.parse(
            model=model,
            max_tokens=DEFAULT_MAX_TOKENS,
            system=EXTRACTION_SYSTEM,
            messages=[{"role": "user", "content": cleaned}],
            output_format=ParsedPosting,
        )
    except Exception as error:
        raise AiRequestError(f"Job posting extraction failed: {error}") from error

    parsed = getattr(response, "parsed_output", None)
    if parsed is None:
        raise AiRequestError("Model returned no structured output for the posting.")
    return parsed


def to_application(
    posting: ParsedPosting, *, description: str | None = None, source: str | None = None
) -> ApplicationCreate:
    """Convert an extracted posting into a create payload.

    Salary is dropped when the band is inverted — a malformed extraction should
    not block tracking the role.
    """
    salary_min, salary_max = posting.salary_min, posting.salary_max
    if salary_min is not None and salary_max is not None and salary_min > salary_max:
        salary_min = salary_max = None

    return ApplicationCreate(
        company=posting.company or "Unknown",
        role=posting.role or "Unknown",
        location=posting.location or None,
        source=source,
        salary_min=salary_min,
        salary_max=salary_max,
        description=description,
    )
