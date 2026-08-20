import pytest

from applytrack import repository as repo
from applytrack.models import Stage
from applytrack.schemas import ApplicationCreate, ApplicationUpdate


def make(session, **overrides):
    payload = {"company": "Acme", "role": "Engineer", **overrides}
    return repo.create_application(session, ApplicationCreate(**payload))


def test_creates_application_at_saved_stage_by_default(session):
    application = make(session)

    assert application.stage is Stage.SAVED


def test_records_an_opening_event_on_creation(session):
    application = make(session)

    assert len(application.events) == 1
    assert application.events[0].from_stage is None


def test_sets_applied_on_when_created_as_applied(session):
    application = make(session, stage=Stage.APPLIED)

    assert application.applied_on is not None


def test_get_raises_for_unknown_id(session):
    with pytest.raises(repo.ApplicationNotFoundError):
        repo.get_application(session, 9999)


def test_change_stage_records_the_transition(session):
    application = make(session)

    repo.change_stage(session, application.id, Stage.APPLIED, note="Submitted")

    events = repo.get_application(session, application.id).events
    assert events[-1].from_stage is Stage.SAVED
    assert events[-1].to_stage is Stage.APPLIED
    assert events[-1].note == "Submitted"


def test_change_stage_backfills_applied_on(session):
    application = make(session)

    updated = repo.change_stage(session, application.id, Stage.APPLIED)

    assert updated.applied_on is not None


def test_change_stage_rejects_a_no_op(session):
    application = make(session)

    with pytest.raises(repo.InvalidStageTransition):
        repo.change_stage(session, application.id, Stage.SAVED)


def test_change_stage_rejects_moving_out_of_a_terminal_stage(session):
    application = make(session)
    repo.change_stage(session, application.id, Stage.REJECTED)

    with pytest.raises(repo.InvalidStageTransition):
        repo.change_stage(session, application.id, Stage.APPLIED)


def test_filters_by_stage(session):
    make(session)
    applied = make(session, stage=Stage.APPLIED)

    results = repo.list_applications(session, stage=Stage.APPLIED)

    assert [a.id for a in results] == [applied.id]


def test_filters_by_company_case_insensitively(session):
    target = make(session, company="Shopify")
    make(session, company="Acme")

    results = repo.list_applications(session, company="shop")

    assert [a.id for a in results] == [target.id]


def test_active_only_excludes_terminal_stages(session):
    live = make(session)
    dead = make(session)
    repo.change_stage(session, dead.id, Stage.REJECTED)

    results = repo.list_applications(session, active_only=True)

    assert [a.id for a in results] == [live.id]


def test_rejects_an_out_of_range_limit(session):
    with pytest.raises(ValueError):
        repo.list_applications(session, limit=0)


def test_rejects_a_negative_offset(session):
    with pytest.raises(ValueError):
        repo.list_applications(session, offset=-1)


def test_update_applies_only_supplied_fields(session):
    application = make(session, location="Toronto")

    updated = repo.update_application(
        session, application.id, ApplicationUpdate(role="Staff Engineer")
    )

    assert updated.role == "Staff Engineer"
    assert updated.location == "Toronto"


def test_update_rejects_an_inverted_salary_band(session):
    application = make(session, salary_min=100, salary_max=200)

    with pytest.raises(ValueError):
        repo.update_application(
            session, application.id, ApplicationUpdate(salary_max=50)
        )


def test_delete_removes_the_application(session):
    application = make(session)

    repo.delete_application(session, application.id)

    with pytest.raises(repo.ApplicationNotFoundError):
        repo.get_application(session, application.id)


def test_stats_counts_totals_and_active(session):
    make(session)
    dead = make(session)
    repo.change_stage(session, dead.id, Stage.WITHDRAWN)

    stats = repo.funnel_stats(session)

    assert stats["total"] == 2
    assert stats["active"] == 1


def test_response_rate_is_zero_without_applications(session):
    assert repo.funnel_stats(session)["response_rate"] == 0.0


def test_response_rate_counts_only_those_that_reached_screen(session):
    heard_back = make(session)
    repo.change_stage(session, heard_back.id, Stage.APPLIED)
    repo.change_stage(session, heard_back.id, Stage.SCREEN)

    ghosted = make(session)
    repo.change_stage(session, ghosted.id, Stage.APPLIED)

    assert repo.funnel_stats(session)["response_rate"] == 0.5
