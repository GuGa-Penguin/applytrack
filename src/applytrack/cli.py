"""Command line interface for applytrack."""

from __future__ import annotations

import argparse
import json
import sys

from . import repository as repo
from .ai import AiNotConfiguredError, AiRequestError, assess_fit, parse_posting, to_application
from .db import build_session_factory, create_db_engine, session_scope
from .models import Stage
from .schemas import ApplicationCreate

EXIT_OK = 0
EXIT_ERROR = 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="applytrack", description="Track job applications from saved to offer."
    )
    parser.add_argument("--database-url", help="Override the database URL.")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="Register a new application.")
    add.add_argument("company")
    add.add_argument("role")
    add.add_argument("--location")
    add.add_argument("--source")
    add.add_argument("--url")
    add.add_argument("--salary-min", type=int)
    add.add_argument("--salary-max", type=int)

    listing = sub.add_parser("list", help="List tracked applications.")
    listing.add_argument("--stage", choices=[s.value for s in Stage])
    listing.add_argument("--company")
    listing.add_argument("--active", action="store_true")

    move = sub.add_parser("stage", help="Move an application to a new stage.")
    move.add_argument("application_id", type=int)
    move.add_argument("to_stage", choices=[s.value for s in Stage])
    move.add_argument("--note")

    sub.add_parser("stats", help="Show funnel statistics.")

    parse = sub.add_parser("parse", help="Parse a job posting with Claude.")
    parse.add_argument("posting_file", help="Path to a file containing the posting.")
    parse.add_argument("--save", action="store_true", help="Also track the parsed role.")
    parse.add_argument("--source")

    score = sub.add_parser("score", help="Score an application against your profile.")
    score.add_argument("application_id", type=int)
    score.add_argument("--profile", required=True, help="Path to your profile file.")

    return parser


def _read_file(path: str) -> str:
    """Read a UTF-8 text file, surfacing a clear error when it is missing."""
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError as error:
        raise OSError(f"could not read {path}: {error}") from error


def _format_row(application) -> str:
    salary = ""
    if application.salary_min and application.salary_max:
        salary = f"  ${application.salary_min:,}-${application.salary_max:,}"
    return (
        f"#{application.id:<4} {application.stage.value:<10} "
        f"{application.company} — {application.role}{salary}"
    )


def main(argv: list[str] | None = None) -> int:
    """Run the CLI. Returns a process exit code."""
    args = _build_parser().parse_args(argv)
    factory = build_session_factory(create_db_engine(args.database_url))

    try:
        with session_scope(factory) as session:
            if args.command == "add":
                application = repo.create_application(
                    session,
                    ApplicationCreate(
                        company=args.company,
                        role=args.role,
                        location=args.location,
                        source=args.source,
                        url=args.url,
                        salary_min=args.salary_min,
                        salary_max=args.salary_max,
                    ),
                )
                print(f"Added #{application.id}: {application.company} — {application.role}")

            elif args.command == "list":
                results = repo.list_applications(
                    session,
                    stage=Stage(args.stage) if args.stage else None,
                    company=args.company,
                    active_only=args.active,
                )
                if not results:
                    print("No applications match those filters.")
                for application in results:
                    print(_format_row(application))

            elif args.command == "stage":
                application = repo.change_stage(
                    session, args.application_id, Stage(args.to_stage), args.note
                )
                print(f"#{application.id} moved to {application.stage.value}")

            elif args.command == "stats":
                print(json.dumps(repo.funnel_stats(session), indent=2))

            elif args.command == "parse":
                posting = parse_posting(_read_file(args.posting_file))
                print(posting.model_dump_json(indent=2))
                if args.save:
                    application = repo.create_application(
                        session,
                        to_application(posting, source=args.source),
                    )
                    print(f"Tracked as #{application.id}")

            elif args.command == "score":
                application = repo.get_application(session, args.application_id)
                posting_text = application.description or (
                    f"{application.role} at {application.company}"
                )
                assessment = assess_fit(posting_text, _read_file(args.profile))
                application.fit_score = assessment.score
                print(assessment.model_dump_json(indent=2))

    except (
        repo.ApplicationNotFoundError,
        repo.InvalidStageTransition,
        AiNotConfiguredError,
        AiRequestError,
        ValueError,
        OSError,
    ) as error:
        print(f"applytrack: {error}", file=sys.stderr)
        return EXIT_ERROR

    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
