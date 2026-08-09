# Plan: Scaffold

## Goal
The repo currently holds only docs, seed data, and tooling — no application. After this plan, `viasel/` contains a **FastAPI backend** and a **Vite/React/TypeScript frontend** that both install, lint, typecheck, and boot, with a health endpoint and a placeholder page. Clean foundation for all later plans (data model, ROM engine, freeze). No business logic yet.

## Success Criteria
- [ ] `cd backend && ruff check . && mypy . && pytest` passes (one health test)
- [ ] `GET /health` returns `{"status":"ok"}`
- [ ] `cd frontend && npm run lint && npx tsc --noEmit && npm run build` passes
- [ ] Frontend dev server renders a "Viasel" placeholder page
- [ ] Nothing outside `backend/` and `frontend/` is modified; `.gitignore` already covers `node_modules/`, `.venv/`, `__pycache__/`

## Files to Read Before Implementing
| File | Why |
|---|---|
| `.gitignore` | confirm `node_modules/`, `.venv/`, `__pycache__/`, `dist/`, `build/` are already ignored — do not duplicate |
| `README.md` | repo layout the scaffold must match (`backend/`, `frontend/`) |

## Known Gotchas
- Use **SQLAlchemy 2.0 typed style** (`Mapped[...]`, `mapped_column`) and **Pydantic v2** (`from_attributes=True`, not `orm_mode`) — plan 01 assumes both.
- `DATABASE_URL` comes from env via `config.py` — never hardcode credentials.
- Postgres does not need to be running for this plan's tests (health test uses TestClient, no DB). DB wiring is verified in plan 01.
- macOS: use `python3 -m venv backend/.venv`; keep the venv inside `backend/` so the ignore rule catches it.

## Tasks
```yaml
- task: 1
  action: CREATE
  file: 'backend/pyproject.toml'
  description: 'Backend deps + tool config'
  instructions:
    - 'Deps: fastapi, uvicorn[standard], sqlalchemy>=2, alembic, psycopg[binary], pydantic>=2, pydantic-settings'
    - 'Dev deps: pytest, ruff, mypy, httpx'
    - 'Add [tool.ruff] line-length=100; [tool.mypy] with python_version=3.12, ignore_missing_imports=true'

- task: 2
  action: CREATE
  file: 'backend/app/config.py'
  description: 'Settings from env'
  instructions:
    - 'pydantic-settings BaseSettings with DATABASE_URL: str'
    - "Default: postgresql+psycopg://viasel:viasel@localhost:5432/viasel"

- task: 3
  action: CREATE
  file: 'backend/app/db.py'
  description: 'Engine + session + Base'
  instructions:
    - 'Create engine from settings.DATABASE_URL; SessionLocal via sessionmaker'
    - 'Define class Base(DeclarativeBase): pass  — models import this in plan 01'
    - 'Expose get_session() dependency that yields a session and closes it'

- task: 4
  action: CREATE
  file: 'backend/app/main.py'
  description: 'FastAPI app + health'
  instructions:
    - 'app = FastAPI(title="Viasel")'
    - 'GET /health returns {"status":"ok"}'
    - 'Leave a commented placeholder: "# routers registered in plan 04"'

- task: 5
  action: CREATE
  file: 'backend/tests/test_health.py'
  description: 'Health test'
  instructions:
    - 'from fastapi.testclient import TestClient; from app.main import app'
    - 'assert client.get("/health").status_code == 200 and .json()["status"] == "ok"'

- task: 6
  action: CREATE
  file: 'backend/alembic.ini and backend/database/migrations/env.py'
  description: 'Alembic wired to Base.metadata'
  instructions:
    - 'alembic init into backend/database/migrations'
    - 'In env.py: target_metadata = app.db.Base.metadata; set sqlalchemy.url from settings.DATABASE_URL'
    - 'Do not create any migration yet — that is plan 01'

- task: 7
  action: CREATE
  file: 'frontend/ (Vite React-TS scaffold)'
  description: 'Vite app + deps + placeholder'
  instructions:
    - 'Scaffold a Vite react-ts project in frontend/'
    - 'Add deps: @tanstack/react-query; add an eslint config'
    - 'App.tsx renders <h1>Viasel</h1>; wrap <App/> in <QueryClientProvider> in main.tsx'
    - 'Create src/services/api.ts: a typed fetch wrapper reading import.meta.env.VITE_API_URL (default http://localhost:8000)'
```

## Validation
### Syntax & Style
```bash
cd backend && ruff check .
cd frontend && npm run lint
```
### Type Safety
```bash
cd backend && mypy .
cd frontend && npx tsc --noEmit
```
### Boot
```bash
cd backend && pytest
cd frontend && npm run build
```

---
*Next: `/execute-plan plans/01-data-model.md` (the five Phase-1 tables). Ask Claude to write it after this scaffold is green.*
