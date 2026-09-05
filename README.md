# Decision Queue

Small Django + DRF API for a product studio to collect partner requests, review them in a queue, and record accept / defer / decline decisions with a short reason.

## Prerequisites

- Docker and Docker Compose
- Git

Database credentials and the Django secret are **not** committed. Create two local env files before the first start.

## Environment setup (required once)

From the repository root (where `docker-compose.yaml` lives):

```bash
# PostgreSQL (used by both the db and app containers)
cat > decisionqueue/db.env << 'EOF'
POSTGRES_DB=mydatabase
POSTGRES_USER=myuser
POSTGRES_PASSWORD=mypassword
EOF

# Django secret — generate your own; do not commit this file
cat > decisionqueue/django.env << 'EOF'
DJANGO_SECRET_KEY=replace-with-a-long-random-string
EOF
```

Generate a secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Paste it as `DJANGO_SECRET_KEY` in `decisionqueue/django.env`.

| File | Variables |
|------|-----------|
| `decisionqueue/db.env` | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` |
| `decisionqueue/django.env` | `DJANGO_SECRET_KEY` |

Compose also sets `DB_HOST=db` on the app container so it reaches Postgres by service name.

## Initialize and run (clean checkout)

```bash
git clone https://github.com/jb-20-a11y/decision-queue
cd decision-queue

# create decisionqueue/db.env and decisionqueue/django.env as above

docker compose up -d --build
docker compose exec django-container python manage.py migrate
```

Migrations are **not** applied automatically; run the `migrate` command after the first start (and after pulling new migrations).

The `django-container` service runs `runserver` on `0.0.0.0:8000`. API base:

`http://localhost:8000/api/`

## Everyday commands

| Action | Command |
|--------|---------|
| Start (detached) | `docker compose up -d --build` |
| Apply migrations | `docker compose exec django-container python manage.py migrate` |
| Stop | `docker compose down` |
| Reset local data | `docker compose down -v` → `docker compose up -d --build` → migrate again |
| Tests | `docker compose exec django-container python manage.py test` |
| Logs | `docker compose logs -f django-container` |

## API sketch

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/items/` | Queue list (50/page). Query: `status` (label or `all`), `ordering` (`id` default or `urgency`) |
| `POST` | `/api/items/` | Create request — body uses **labels** for urgency and expected impact; status is set to Pending |
| `POST` | `/api/items/<id>/` | Record decision — `status` label (Accepted / Deferred / Declined) + `status_reason` |

## Completed requirements

- Create a request (title, problem statement, expected impact, urgency)
- View the queue; filter by status; sort by urgency (highest first) or primary key
- Record accept / defer / decline with a short reason
- Docker Compose: app + PostgreSQL; data in a named volume; migrations included (run manually)
- Serializer validation; automated tests for the core workflow (13 tests)
- Fictional data only

## Known gaps

- No browser UI (API-only; DRF browsable API available while `DEBUG=True`)
- No delete (or archive) endpoint for items
- No authentication
- No seed command for demo data outside tests
- Env files must be created locally (secrets not committed)

## Important decisions

### 1. Database design (single table, field choices, no lookup tables)

**One row per request, including the current decision.**  
The brief asks to record a decision, not a history of decision attempts. Status and `status_reason` live on `Item`. A separate `Decision` table and join would only help if we needed an audit trail of status changes; for “current state of the queue” they add complexity without benefit.

**Field-level choices:**

| Field | Type | Why |
|-------|------|-----|
| `title` | `CharField(max_length=100)` | Short, list-friendly label; bounded length keeps indexes and UI rows predictable |
| `problem_statement` | `TextField` | Unbounded narrative; partners may need room to explain context |
| `urgency` / `expected_impact` | `IntegerField` + `IntegerChoices` | Small integers sort and compare cheaply; descending index on urgency supports “highest first” via Postgres B-tree |
| `status` | `IntegerField` + `IntegerChoices` | Low-cardinality equality filter (Pending / Deferred / Accepted / Declined) |
| `status_reason` | `TextField` | Free-form rationale when a decision is recorded |
| `date_created` | `DateTimeField(auto_now_add=True)` | Set once when the request is created |
| `date_modified` | `DateTimeField(auto_now=True)` | Advances on every save (including decision updates) |

Fully normalized label tables (`urgency_id` → `urgency_labels`) were considered and rejected. Levels are a fixed, small set for this product; a join (or extra migration every time a label changes) is unnecessary complexity. Integers stay in the database for portability and sortability; human-readable labels are applied at the API boundary (see below). If levels later need to be added/removed/renamed often, a lookup table would become justified—until then, `IntegerChoices` plus serializers is enough.

### 2. Labels on the wire, integers in the database

Serializers use a shared `IntegerChoiceField` so JSON always speaks labels (`"High"`, `"Accepted"`) while PostgreSQL stores integers. That:

- Keeps list/create/update contracts consistent and readable
- Decouples any future UI (or other client) from internal numbering—if values were renumbered, clients would not need changes
- Avoids exposing implementation details that only matter for indexing and ordering

The same mapping is used on list, create, and update serializers so there is one choice contract for the whole API.

### 3. REST API as the product surface (UI-agnostic), with pagination

Create, queue (filter / sort / paginate), and decide are HTTP endpoints with tests. The API is intentionally UI-agnostic: a React SPA, Django templates, or the DRF browsable API can all sit on the same label-based contract without backend changes.

List responses are paginated at **50 items per page**. The product may keep requests indefinitely; without a page size, a large queue would overwhelm any UI (or client) that renders the full list. Pagination, status filter, and urgency ordering together give a controllable window over a growing table. Within the time box, delivering that contract with Compose, migrations, and tests was more reliable than a half-finished frontend.

## What I would do next

- Add delete or soft-archive if the queue should not grow without bound
- Add a simple UI on the existing endpoints
- If decision history is required: a `Decision` table with `Item.status` kept as the denormalized current value

## Time spent

**Total Time:** 5 hours, 59 minutes
