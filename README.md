# applytrack

Track job applications from *saved* through to *offer*, with a real funnel and
an honest response rate — not a spreadsheet you stop updating in week three.

```console
$ applytrack add Shopify "Senior .NET Engineer" --source LinkedIn --salary-min 120000 --salary-max 160000
Added #1: Shopify — Senior .NET Engineer

$ applytrack stage 1 applied --note "Referred by Sam"
#1 moved to applied

$ applytrack list
#1    applied    Shopify — Senior .NET Engineer  $120,000-$160,000
```

## Why

Most trackers are a flat list with a status column. That tells you where things
are, but not what is working. `applytrack` records every stage transition as an
immutable event, so the pipeline can answer the question that actually matters:
**of the roles I applied to, how many ever replied?**

## Install

```console
pip install -e ".[dev]"
```

## The funnel

```
saved → applied → screen → interview → onsite → offer
                                         ↘ rejected / withdrawn
```

`offer`, `rejected`, and `withdrawn` are terminal — once an application lands
there its stage is frozen, so history stays truthful. Every move is written to
`status_events` with the stage it came from, the stage it went to, an optional
note, and a timestamp.

## CLI

| Command | What it does |
| --- | --- |
| `applytrack add COMPANY ROLE` | Register an application (`--location`, `--source`, `--url`, `--salary-min/max`) |
| `applytrack list` | List applications (`--stage`, `--company`, `--active`) |
| `applytrack stage ID TO_STAGE` | Move a stage, recording the transition (`--note`) |
| `applytrack stats` | Funnel counts and response rate as JSON |

Point any command at a different database with `--database-url`, or set
`APPLYTRACK_DATABASE_URL`.

## HTTP API

```console
uvicorn applytrack.api:app --reload
```

Interactive docs at `http://127.0.0.1:8000/docs`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Liveness check |
| `POST` | `/applications` | Create an application |
| `GET` | `/applications` | List with `stage`, `company`, `active_only`, `limit`, `offset` |
| `GET` | `/applications/{id}` | One application with its full event history |
| `PATCH` | `/applications/{id}` | Partial update |
| `POST` | `/applications/{id}/stage` | Move to a new stage |
| `DELETE` | `/applications/{id}` | Remove an application and its history |
| `GET` | `/stats` | Funnel counts and response rate |

Invalid stage moves return **409**, unknown ids **404**, and bad payloads
**422** — including an inverted salary band, which is rejected rather than
stored.

## Response rate

```json
{
  "total": 24,
  "active": 9,
  "by_stage": { "saved": 3, "applied": 12, "screen": 4, "offer": 1, "rejected": 4 },
  "response_rate": 0.4167
}
```

`response_rate` is the share of applications that **ever reached `screen` or
beyond**, over those that **ever reached `applied`**. It is computed from the
event history rather than current stage, so an application that was screened and
later rejected still counts as a response.

## Development

```console
python -m venv .venv && .venv/Scripts/activate
pip install -e ".[dev]"
pytest --cov=applytrack --cov-report=term-missing
```

## License

MIT
