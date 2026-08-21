import pytest

from applytrack.cli import main


@pytest.fixture()
def db_url(tmp_path):
    return f"sqlite:///{tmp_path / 'cli.db'}"


def run(db_url, *args):
    return main(["--database-url", db_url, *args])


def test_add_reports_the_new_id(db_url, capsys):
    exit_code = run(db_url, "add", "Shopify", "Senior Engineer")

    assert exit_code == 0
    assert "Added #1" in capsys.readouterr().out


def test_list_shows_added_applications(db_url, capsys):
    run(db_url, "add", "Shopify", "Senior Engineer")
    capsys.readouterr()

    run(db_url, "list")

    assert "Shopify" in capsys.readouterr().out


def test_list_reports_when_nothing_matches(db_url, capsys):
    run(db_url, "list")

    assert "No applications match" in capsys.readouterr().out


def test_list_filters_by_active_flag(db_url, capsys):
    run(db_url, "add", "Acme", "Engineer")
    run(db_url, "stage", "1", "rejected")
    capsys.readouterr()

    run(db_url, "list", "--active")

    assert "No applications match" in capsys.readouterr().out


def test_stage_moves_the_application(db_url, capsys):
    run(db_url, "add", "Acme", "Engineer")
    capsys.readouterr()

    exit_code = run(db_url, "stage", "1", "applied", "--note", "Sent")

    assert exit_code == 0
    assert "moved to applied" in capsys.readouterr().out


def test_stage_reports_an_unknown_application(db_url, capsys):
    exit_code = run(db_url, "stage", "99", "applied")

    assert exit_code == 1
    assert "applytrack:" in capsys.readouterr().err


def test_stage_reports_an_invalid_transition(db_url, capsys):
    run(db_url, "add", "Acme", "Engineer")
    capsys.readouterr()

    exit_code = run(db_url, "stage", "1", "saved")

    assert exit_code == 1
    assert "applytrack:" in capsys.readouterr().err


def test_stats_emits_json(db_url, capsys):
    run(db_url, "add", "Acme", "Engineer")
    capsys.readouterr()

    run(db_url, "stats")

    assert '"total": 1' in capsys.readouterr().out


def test_add_rejects_an_inverted_salary_band(db_url, capsys):
    exit_code = run(
        db_url, "add", "Acme", "Engineer", "--salary-min", "200", "--salary-max", "100"
    )

    assert exit_code == 1


@pytest.fixture()
def stub_ai(monkeypatch):
    """Replace the AI calls so the CLI can be exercised without credentials."""
    from applytrack.ai.schemas import FitAssessment, ParsedPosting, Recommendation

    posting = ParsedPosting(company="Shopify", role="Senior Engineer", salary_min=120000)
    assessment = FitAssessment(score=77, recommendation=Recommendation.APPLY)

    monkeypatch.setattr("applytrack.cli.parse_posting", lambda text: posting)
    monkeypatch.setattr(
        "applytrack.cli.assess_fit", lambda posting_text, profile: assessment
    )
    return posting, assessment


def test_parse_prints_the_extracted_posting(db_url, tmp_path, capsys, stub_ai):
    posting_file = tmp_path / "posting.txt"
    posting_file.write_text("Senior Engineer at Shopify", encoding="utf-8")

    exit_code = run(db_url, "parse", str(posting_file))

    assert exit_code == 0
    assert '"company": "Shopify"' in capsys.readouterr().out


def test_parse_with_save_tracks_the_role(db_url, tmp_path, capsys, stub_ai):
    posting_file = tmp_path / "posting.txt"
    posting_file.write_text("Senior Engineer at Shopify", encoding="utf-8")

    run(db_url, "parse", str(posting_file), "--save", "--source", "LinkedIn")

    assert "Tracked as #1" in capsys.readouterr().out


def test_parse_reports_a_missing_file(db_url, capsys, stub_ai):
    exit_code = run(db_url, "parse", "does-not-exist.txt")

    assert exit_code == 1
    assert "applytrack:" in capsys.readouterr().err


def test_score_prints_the_assessment(db_url, tmp_path, capsys, stub_ai):
    profile = tmp_path / "profile.txt"
    profile.write_text("Six years of C#", encoding="utf-8")
    run(db_url, "add", "Acme", "Engineer")
    capsys.readouterr()

    exit_code = run(db_url, "score", "1", "--profile", str(profile))

    assert exit_code == 0
    assert '"score": 77' in capsys.readouterr().out


def test_score_reports_an_unknown_application(db_url, tmp_path, capsys, stub_ai):
    profile = tmp_path / "profile.txt"
    profile.write_text("Six years of C#", encoding="utf-8")

    exit_code = run(db_url, "score", "99", "--profile", str(profile))

    assert exit_code == 1
