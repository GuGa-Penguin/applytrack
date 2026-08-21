import pytest
from fastapi.testclient import TestClient

from applytrack.ai import AiNotConfiguredError, AiRequestError
from applytrack.ai.schemas import FitAssessment, ParsedPosting, Recommendation
from applytrack.api import create_app
from tests.fakes import FakeAnthropic

POSTING = ParsedPosting(
    company="Shopify",
    role="Senior .NET Engineer",
    location="Montreal, QC",
    salary_min=120000,
    salary_max=160000,
    required_skills=["C#"],
)

ASSESSMENT = FitAssessment(score=81, recommendation=Recommendation.APPLY)


def build(tmp_path, fake):
    app = create_app(f"sqlite:///{tmp_path / 'ai.db'}")
    app.dependency_overrides[app.state.ai_dependency] = lambda: fake
    return TestClient(app)


@pytest.fixture()
def parsing_client(tmp_path):
    with build(tmp_path, FakeAnthropic(parsed=POSTING)) as client:
        yield client


def test_parses_a_posting(parsing_client):
    response = parsing_client.post("/postings/parse", json={"text": "Job posting body"})

    assert response.status_code == 200
    assert response.json()["company"] == "Shopify"


def test_rejects_an_empty_posting_body(parsing_client):
    response = parsing_client.post("/postings/parse", json={"text": ""})

    assert response.status_code == 422


def test_imports_a_posting_as_a_tracked_application(parsing_client):
    response = parsing_client.post(
        "/postings/import", json={"text": "Job posting body", "source": "LinkedIn"}
    )

    assert response.status_code == 201
    assert response.json()["company"] == "Shopify"
    assert response.json()["source"] == "LinkedIn"


def test_imported_application_starts_at_saved(parsing_client):
    body = parsing_client.post("/postings/import", json={"text": "Job posting"}).json()

    assert body["stage"] == "saved"


def test_import_reports_upstream_failure_as_502(tmp_path):
    with build(tmp_path, FakeAnthropic(error=RuntimeError("boom"))) as client:
        response = client.post("/postings/import", json={"text": "Job posting"})

    assert response.status_code == 502


def test_parse_reports_upstream_failure_as_502(tmp_path):
    with build(tmp_path, FakeAnthropic(error=RuntimeError("boom"))) as client:
        response = client.post("/postings/parse", json={"text": "Job posting"})

    assert response.status_code == 502


def test_parse_reports_missing_credentials_as_503(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'ai.db'}")

    def unconfigured():
        raise AiNotConfiguredError("no credentials")

    app.dependency_overrides[app.state.ai_dependency] = unconfigured
    with TestClient(app) as client:
        response = client.post("/postings/parse", json={"text": "Job posting"})

    assert response.status_code == 503


def test_scores_an_application_and_persists_the_score(tmp_path):
    with build(tmp_path, FakeAnthropic(parsed=ASSESSMENT)) as client:
        created = client.post(
            "/applications", json={"company": "Acme", "role": "Engineer"}
        ).json()

        response = client.post(
            f"/applications/{created['id']}/score",
            json={"profile": "Six years of C# and EF Core."},
        )

        assert response.status_code == 200
        assert response.json()["score"] == 81
        assert client.get(f"/applications/{created['id']}").json()["fit_score"] == 81


def test_score_returns_404_for_an_unknown_application(tmp_path):
    with build(tmp_path, FakeAnthropic(parsed=ASSESSMENT)) as client:
        response = client.post(
            "/applications/4242/score", json={"profile": "profile text"}
        )

    assert response.status_code == 404


def test_score_rejects_an_empty_profile(tmp_path):
    with build(tmp_path, FakeAnthropic(parsed=ASSESSMENT)) as client:
        created = client.post(
            "/applications", json={"company": "Acme", "role": "Engineer"}
        ).json()

        response = client.post(
            f"/applications/{created['id']}/score", json={"profile": ""}
        )

    assert response.status_code == 422


def test_score_reports_upstream_failure_as_502(tmp_path):
    with build(tmp_path, FakeAnthropic(error=AiRequestError("upstream"))) as client:
        created = client.post(
            "/applications", json={"company": "Acme", "role": "Engineer"}
        ).json()

        response = client.post(
            f"/applications/{created['id']}/score", json={"profile": "profile text"}
        )

    assert response.status_code == 502
