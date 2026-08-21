"""AI-assisted parsing and scoring, powered by Claude."""

from .client import DEFAULT_MODEL, AiNotConfiguredError, AiRequestError, build_client
from .extract import parse_posting, to_application
from .schemas import FitAssessment, ParsedPosting, Recommendation, RemotePolicy
from .score import assess_fit

__all__ = [
    "DEFAULT_MODEL",
    "AiNotConfiguredError",
    "AiRequestError",
    "FitAssessment",
    "ParsedPosting",
    "Recommendation",
    "RemotePolicy",
    "assess_fit",
    "build_client",
    "parse_posting",
    "to_application",
]
