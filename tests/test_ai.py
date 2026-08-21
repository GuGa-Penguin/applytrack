import pytest

from applytrack.ai import (
    AiRequestError,
    FitAssessment,
    ParsedPosting,
    Recommendation,
    RemotePolicy,
    assess_fit,
    parse_posting,
    to_application,
)
from applytrack.ai.client import DEFAULT_MODEL, MAX_POSTING_CHARS
from tests.fakes import FakeAnthropic

POSTING = ParsedPosting(
    company="Shopify",
    role="Senior .NET Engineer",
    location="Montreal, QC",
    remote_policy=RemotePolicy.HYBRID,
    salary_min=120000,
    salary_max=160000,
    currency="CAD",
    required_skills=["C#", "EF Core"],
)

ASSESSMENT = FitAssessment(
    score=72,
    recommendation=Recommendation.APPLY,
    strengths=["Six years of EF Core"],
    gaps=["No Kubernetes experience"],
)


def test_returns_the_parsed_posting():
    client = FakeAnthropic(parsed=POSTING)

    result = parse_posting("Senior .NET Engineer at Shopify", client=client)

    assert result.company == "Shopify"


def test_requests_the_default_model():
    client = FakeAnthropic(parsed=POSTING)

    parse_posting("some posting text", client=client)

    assert client.calls[0]["model"] == DEFAULT_MODEL


def test_requests_structured_output_against_the_schema():
    client = FakeAnthropic(parsed=POSTING)

    parse_posting("some posting text", client=client)

    assert client.calls[0]["output_format"] is ParsedPosting


def test_sends_trimmed_posting_text():
    client = FakeAnthropic(parsed=POSTING)

    parse_posting("   padded posting   ", client=client)

    assert client.calls[0]["messages"][0]["content"] == "padded posting"


def test_rejects_empty_posting_text():
    with pytest.raises(ValueError):
        parse_posting("   ", client=FakeAnthropic(parsed=POSTING))


def test_rejects_non_string_posting_text():
    with pytest.raises(TypeError):
        parse_posting(None, client=FakeAnthropic(parsed=POSTING))


def test_rejects_oversized_posting_text():
    with pytest.raises(ValueError):
        parse_posting("x" * (MAX_POSTING_CHARS + 1), client=FakeAnthropic(parsed=POSTING))


def test_wraps_sdk_errors():
    client = FakeAnthropic(error=RuntimeError("connection reset"))

    with pytest.raises(AiRequestError):
        parse_posting("posting", client=client)


def test_raises_when_no_structured_output_returned():
    client = FakeAnthropic(parsed=None)

    with pytest.raises(AiRequestError):
        parse_posting("posting", client=client)


def test_to_application_maps_extracted_fields():
    draft = to_application(POSTING, source="LinkedIn")

    assert draft.company == "Shopify"
    assert draft.salary_min == 120000
    assert draft.source == "LinkedIn"


def test_to_application_drops_an_inverted_salary_band():
    posting = POSTING.model_copy(update={"salary_min": 200000, "salary_max": 100000})

    draft = to_application(posting)

    assert draft.salary_min is None
    assert draft.salary_max is None


def test_to_application_falls_back_when_company_missing():
    posting = POSTING.model_copy(update={"company": "", "role": ""})

    draft = to_application(posting)

    assert draft.company == "Unknown"
    assert draft.role == "Unknown"


def test_to_application_stores_the_description_when_given():
    draft = to_application(POSTING, description="raw posting body")

    assert draft.description == "raw posting body"


def test_assess_fit_returns_the_assessment():
    client = FakeAnthropic(parsed=ASSESSMENT)

    result = assess_fit(POSTING, "Six years of C# and EF Core.", client=client)

    assert result.score == 72
    assert result.recommendation is Recommendation.APPLY


def test_assess_fit_serialises_a_parsed_posting_into_the_prompt():
    client = FakeAnthropic(parsed=ASSESSMENT)

    assess_fit(POSTING, "profile text", client=client)

    assert "Shopify" in client.calls[0]["messages"][0]["content"]


def test_assess_fit_accepts_raw_posting_text():
    client = FakeAnthropic(parsed=ASSESSMENT)

    result = assess_fit("Senior Engineer at Acme", "profile text", client=client)

    assert result.score == 72


def test_assess_fit_rejects_an_empty_profile():
    with pytest.raises(ValueError):
        assess_fit(POSTING, "   ", client=FakeAnthropic(parsed=ASSESSMENT))


def test_assess_fit_rejects_a_non_string_profile():
    with pytest.raises(TypeError):
        assess_fit(POSTING, None, client=FakeAnthropic(parsed=ASSESSMENT))


def test_assess_fit_wraps_sdk_errors():
    client = FakeAnthropic(error=RuntimeError("rate limited"))

    with pytest.raises(AiRequestError):
        assess_fit(POSTING, "profile", client=client)


def test_assess_fit_raises_when_no_structured_output():
    with pytest.raises(AiRequestError):
        assess_fit(POSTING, "profile", client=FakeAnthropic(parsed=None))


def test_score_must_be_within_zero_to_one_hundred():
    with pytest.raises(ValueError):
        FitAssessment(score=140, recommendation=Recommendation.APPLY)
