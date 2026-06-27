# IWALLET

Telegram WebApp shaxsiy moliyaviy tracker — voice-first, o'zbek tilida.

📖 Planning hujjatlari: [docs/](docs/) (PRD, UX, Architecture, Project Context, Epics, Readiness Report).

## Local Development Setup

### Prerequisites

- Python 3.13+
- Docker Desktop (Postgres + Redis containers)
- Node 22+ (Tailwind CLI — Story 0.6+)

### First-time setup

```powershell
# 1. Clone + venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip

# 2. Install Python deps
pip install -r requirements-dev.txt

# 3. Copy env template
Copy-Item .env.example .env
# Edit .env — fill TELEGRAM_BOT_TOKEN, GEMINI_API_KEY (optional for v0.1)

# 4. Start Postgres + Redis
docker-compose -f docker-compose.dev.yml up -d

# 5. Configure .env to use Postgres
# In .env, set:
#   DATABASE_URL=postgres://iwallet:iwallet_dev@localhost:5432/iwallet

# 6. Migrate
python manage.py migrate

# 7. Run dev server (uvicorn ASGI for async voice endpoints)
uvicorn iwallet.asgi:application --reload --port 8000
```

### Running tests

```powershell
pytest -q                    # full suite
pytest --cov=. --cov-report=term-missing  # with coverage
```

### Lint + format

```powershell
ruff check .       # lint
ruff format .      # format
djlint --check .   # template lint (later stories)
```

### Stopping dev containers

```powershell
docker-compose -f docker-compose.dev.yml down       # stop
docker-compose -f docker-compose.dev.yml down -v    # stop + wipe data
```

## Sprint Status

- Sprint 0 (Project Foundation) — in progress
  - ✅ Story 0.1 — Django + 10 apps scaffold
  - ✅ Story 0.2 — Single settings.py + .env loading
  - 🔄 Story 0.3 — PostgreSQL + initial migration
  - ⏳ 0.4-0.9

See [docs/epics.md](docs/epics.md) for full story breakdown.
