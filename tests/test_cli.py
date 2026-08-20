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
