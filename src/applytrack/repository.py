"""Data access and funnel rules for tracked applications."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .models import STAGE_ORDER, Application, Stage, StatusEvent
from .schemas import ApplicationCreate, ApplicationUpdate

#: Reaching this stage counts as a response from the employer.
RESPONDED_FROM = Stage.SCREEN


class ApplicationNotFoundError(LookupError):
    """Raised when no application matches the requested id."""


class InvalidStageTransition(ValueError):
    """Raised when a stage change is not permitted."""


def _stage_index(stage: Stage) -> int:
    """Return the funnel position, or -1 for stages outside the ladder."""
    return STAGE_ORDER.index(stage) if stage in STAGE_ORDER else -1


def create_application(session: Session, payload: ApplicationCreate) -> Application:
    """Insert a new application and record its opening event."""
    application = Application(**payload.model_dump())
    if application.stage is Stage.APPLIED and application.applied_on is None:
        application.applied_on = date.today()

    # Append through the relationship so the in-memory collection stays in sync.
    application.events.append(
        StatusEvent(
            from_stage=None,
            to_stage=application.stage,
            note="Application created",
        )
    )
    session.add(application)
    session.flush()
    return application


def get_application(session: Session, application_id: int) -> Application:
    """Return one application with its events, or raise."""
    statement = (
        select(Application)
        .options(selectinload(Application.events))
        .where(Application.id == application_id)
    )
    application = session.execute(statement).scalar_one_or_none()
    if application is None:
        raise ApplicationNotFoundError(f"No application with id {application_id}")
    return application


def list_applications(
    session: Session,
    *,
    stage: Stage | None = None,
    company: str | None = None,
    active_only: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> list[Application]:
    """Return applications matching the supplied filters, newest first."""
    if limit < 1 or limit > 500:
        raise ValueError("limit must be between 1 and 500")
    if offset < 0:
        raise ValueError("offset must not be negative")

    statement = select(Application).options(selectinload(Application.events))
    if stage is not None:
        statement = statement.where(Application.stage == stage)
    if company:
        statement = statement.where(Application.company.ilike(f"%{company}%"))
    if active_only:
        active = [s for s in Stage if s.is_active]
        statement = statement.where(Application.stage.in_(active))

    statement = statement.order_by(Application.created_at.desc()).limit(limit).offset(offset)
    return list(session.execute(statement).scalars().all())


def update_application(
    session: Session, application_id: int, payload: ApplicationUpdate
) -> Application:
    """Apply a partial update to an existing application."""
    application = get_application(session, application_id)
    changes = payload.model_dump(exclude_unset=True)

    merged_min = changes.get("salary_min", application.salary_min)
    merged_max = changes.get("salary_max", application.salary_max)
    if merged_min is not None and merged_max is not None and merged_min > merged_max:
        raise ValueError("salary_min must not exceed salary_max")

    for field, value in changes.items():
        setattr(application, field, value)
    session.flush()
    return application


def change_stage(
    session: Session, application_id: int, to_stage: Stage, note: str | None = None
) -> Application:
    """Move an application to a new stage, recording the transition."""
    application = get_application(session, application_id)
    current = application.stage

    if current is to_stage:
        raise InvalidStageTransition(f"Application is already at stage {to_stage.value}")
    if current.is_terminal:
        raise InvalidStageTransition(
            f"Stage {current.value} is terminal and cannot be changed"
        )

    application.events.append(
        StatusEvent(from_stage=current, to_stage=to_stage, note=note)
    )
    application.stage = to_stage
    if to_stage is Stage.APPLIED and application.applied_on is None:
        application.applied_on = date.today()

    session.flush()
    return application


def delete_application(session: Session, application_id: int) -> None:
    """Remove an application and its history."""
    session.delete(get_application(session, application_id))
    session.flush()


def funnel_stats(session: Session) -> dict[str, object]:
    """Return counts per stage plus the employer response rate."""
    counts = dict(
        session.execute(
            select(Application.stage, func.count(Application.id)).group_by(
                Application.stage
            )
        ).all()
    )
    by_stage = {stage.value: int(counts.get(stage, 0)) for stage in Stage}
    total = sum(by_stage.values())
    active = sum(by_stage[s.value] for s in Stage if s.is_active)

    applied_ids = set(
        session.execute(
            select(StatusEvent.application_id).where(
                StatusEvent.to_stage == Stage.APPLIED
            )
        )
        .scalars()
        .all()
    )
    responded_stages = [s for s in STAGE_ORDER if _stage_index(s) >= _stage_index(RESPONDED_FROM)]
    responded_ids = set(
        session.execute(
            select(StatusEvent.application_id).where(
                StatusEvent.to_stage.in_(responded_stages)
            )
        )
        .scalars()
        .all()
    )

    denominator = len(applied_ids)
    rate = len(applied_ids & responded_ids) / denominator if denominator else 0.0

    return {
        "total": total,
        "active": active,
        "by_stage": by_stage,
        "response_rate": round(rate, 4),
    }
