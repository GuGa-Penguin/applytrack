"""FastAPI application exposing the tracker over HTTP."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.orm import Session

from . import repository as repo
from .db import build_session_factory, create_db_engine
from .models import Stage
from .schemas import (
    ApplicationCreate,
    ApplicationRead,
    ApplicationUpdate,
    FunnelStats,
    StageChange,
)

DEFAULT_PAGE_SIZE = 50


def create_app(database_url: str | None = None) -> FastAPI:
    """Build the FastAPI app, wiring it to the given database."""
    engine = create_db_engine(database_url)
    session_factory = build_session_factory(engine)

    app = FastAPI(
        title="applytrack",
        version="0.1.0",
        description="Track job applications from saved through to offer.",
    )
    app.state.session_factory = session_factory

    def get_session() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(
        "/applications",
        response_model=ApplicationRead,
        status_code=status.HTTP_201_CREATED,
    )
    def create(payload: ApplicationCreate, session: Session = Depends(get_session)):
        return repo.create_application(session, payload)

    @app.get("/applications", response_model=list[ApplicationRead])
    def index(
        session: Session = Depends(get_session),
        stage: Stage | None = None,
        company: str | None = None,
        active_only: bool = False,
        limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ):
        return repo.list_applications(
            session,
            stage=stage,
            company=company,
            active_only=active_only,
            limit=limit,
            offset=offset,
        )

    @app.get("/applications/{application_id}", response_model=ApplicationRead)
    def show(application_id: int, session: Session = Depends(get_session)):
        try:
            return repo.get_application(session, application_id)
        except repo.ApplicationNotFoundError as error:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error

    @app.patch("/applications/{application_id}", response_model=ApplicationRead)
    def update(
        application_id: int,
        payload: ApplicationUpdate,
        session: Session = Depends(get_session),
    ):
        try:
            return repo.update_application(session, application_id, payload)
        except repo.ApplicationNotFoundError as error:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
        except ValueError as error:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error

    @app.post("/applications/{application_id}/stage", response_model=ApplicationRead)
    def move_stage(
        application_id: int,
        payload: StageChange,
        session: Session = Depends(get_session),
    ):
        try:
            return repo.change_stage(
                session, application_id, payload.to_stage, payload.note
            )
        except repo.ApplicationNotFoundError as error:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
        except repo.InvalidStageTransition as error:
            raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error

    @app.delete("/applications/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
    def destroy(application_id: int, session: Session = Depends(get_session)):
        try:
            repo.delete_application(session, application_id)
        except repo.ApplicationNotFoundError as error:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error

    @app.get("/stats", response_model=FunnelStats)
    def stats(session: Session = Depends(get_session)):
        return repo.funnel_stats(session)

    return app


app = create_app()
