# CreatorRetain

The operating system for long-term creator and brand partnerships.

Currently under active development.

## Running it

Both halves have to be running. The web app fetches the workspace
before it renders any signed-in page, so a frontend on its own does
not partly work - it fails to load.

```powershell
.\dev.ps1
```

That opens two windows:

| | |
|---|---|
| API | http://127.0.0.1:8000 — Swagger at `/docs` |
| Web | http://localhost:3000 |

The web app defaults to `http://127.0.0.1:8000`, so nothing needs
configuring for local work. Set `NEXT_PUBLIC_API_URL` in
`apps/web/.env.local` only when the API is somewhere else.

To run one at a time, in the window you are already in:

```powershell
.\dev.ps1 -Api
.\dev.ps1 -Web
```

Or by hand, in two windows:

```powershell
cd apps\api
uv run uvicorn app.main:app --reload --port 8000
```

```powershell
cd apps\web
pnpm dev
```

### After pulling changes

```powershell
cd apps\api
uv sync                      # if dependencies changed
uv run alembic upgrade head  # if there is a new migration

cd ..\web
pnpm install                 # if dependencies changed
```

If the frontend behaves as though an edit never happened, delete
`apps\web\.next` and start it again. Turbopack occasionally serves
a stale build after files are replaced underneath it rather than
edited in place.

## Checking it still works

Each module has an end-to-end suite that runs the real app against
in-memory SQLite. No database setup, no fixtures, nothing to clean
up afterwards.

```powershell
cd apps\api
uv run python verify_creator_profile.py
uv run python verify_discovery.py
uv run python verify_entitlements.py
uv run python verify_collaboration.py
uv run python verify_retainers.py
uv run python verify_brand.py
```

## Layout

```
apps/api    FastAPI, SQLAlchemy, Alembic, PostgreSQL
apps/web    Next.js App Router, Tailwind
docs        PRD and feature notes
```
