---
stepsCompleted:
  - step-01-init
  - step-02-context
  - step-03-starter
  - step-04-decisions
  - step-05-patterns
  - step-06-structure
  - step-07-validation
  - step-08-complete
inputDocuments:
  - docs/product-brief.md
  - docs/prd.md
  - docs/ux-design-specification.md
workflowType: 'architecture'
project_name: 'IWALLET'
user_name: 'Eric'
date: '2026-06-25'
---

# Architecture Decision Document — IWALLET

**Author:** Eric (Winston facilitating)
**Date:** 2026-06-25
**Status:** Complete — ready for implementation

---

## Project Context Analysis

### Requirements Overview

**Functional Requirements:** PRD'da 64 ta FR (FR1-FR64), 10 ta capability area bo'yicha guruhlangan:

- Authentication & Onboarding (FR1-FR4)
- Transaction Management (FR5-FR9)
- Manual Input (FR10-FR13)
- Voice Input (FR14-FR25) — **eng kompleks**, 12 ta FR
- Categories (FR26-FR29)
- Debt Management (FR30-FR38) — **state machine talab qiladi**
- Multi-Currency (FR39-FR44)
- Recurring Transactions (FR45-FR49)
- Reports & Analytics (FR50-FR55)
- Notifications (FR56-FR58) — **alohida bot process**
- History & Search (FR59-FR61)
- Settings (FR62-FR64)

**Non-Functional Requirements:** 34 ta NFR — performance (voice p50 <3s), security (initData HMAC, no audio storage, Decimal), scalability (50 concurrent voice), reliability (CBU fallback), accessibility (WCAG AA), code quality (SOLID, lint, ≥80% test coverage).

### Scale & Complexity

- **Complexity level:** medium-high (voice AI integratsiya + Telegram WebApp + multi-process + state machine bilan)
- **Primary domain:** server-rendered web app (Django + htmx) — full-stack monorepo
- **Architectural components (estimated):**
  - 1 ta WebApp (Django) — HTTP, htmx swap, voice endpoint
  - 1 ta Telegram Bot service (alohida process) — push, deep-link
  - 1 ta async voice pipeline (Django async views)
  - 1 ta cron service (recurring + CBU fetch)
  - 1 ta PostgreSQL DB
  - External: Gemini API, CBU.uz, Telegram Bot/WebApp API

### Technical Constraints & Dependencies

| Constraint | Sabab | Implikatsiya |
|---|---|---|
| Telegram WebApp only | PRD scope | No standalone PWA, no native — single deployment, mobile viewport lock |
| Django + htmx (no SPA) | Eric'ning xohishi, server-rendered | Templates `templates/` da, JS minimum (htmx + Alpine) |
| Voice pipeline blocks WSGI | Gemini 2-5s latency | **Async views majburiy** (Django ≥4.1) |
| Audio not stored | NFR9, privacy | In-memory only, Gemini'ga stream qilinadi |
| Bot va WebApp alohida | NFR23 | Ikkita gunicorn/uvicorn process, bitta DB |
| Decimal precision | NFR12, accounting | `DecimalField(max_digits=15, decimal_places=2)`, never Float |
| O'zbek voice | PRD differentiator | Gemini `gemini-2.0-flash` (audio + intent in single call) |

### Cross-Cutting Concerns Identified

1. **Authentication** — Telegram WebApp `initData` HMAC validation har request'da (NFR6), shared bot+webapp `User` model orqali (FR2)
2. **Currency conversion (display)** — har balansga ko'rsatishda CBU.uz cache'ga murojaat (FR41-43)
3. **Voice STT + parse pipeline** — async, Gemini API, multi-tx support (FR14-25)
4. **Debt state machine** — `open` → `partial` → `closed` (FR34-37), reusable model logic
5. **Notification scheduler** — cron yoki Celery beat (FR46, 56, 57)
6. **Privacy/security boundary** — audio handling, initData per-request, no PII in logs
7. **htmx swap atomicity** — har endpoint partial template qaytaradi (multi-transaction confirm screen uchun kritik)
8. **i18n (single language v1)** — barcha string'lar markdown/templates'da uzbek, kelajakda kengaytirishga ochiq

---

## Starter Template Evaluation

### Primary Technology Domain

Server-rendered Django web app + alohida bot service + Postgres. **Django ecosystem'da production-ready starter template'lar kam** (mostly djangopackages.org single-purpose). Asosiy variantlar:

| Variant | Holat | Tahlil |
|---|---|---|
| `django-admin startproject` | Vanilla | Eng odatiy, minimal, sodda, biz nazoratimiz to'liq |
| **cookiecutter-django** | Mature | Battery-included (Postgres, Redis, Celery, Docker), **lekin React-leaning, htmx native emas** |
| `django-htmx` package | Add-on | htmx integration tezroq, lekin starter emas |
| Falco (Django + htmx + Tailwind) | Niche, newer | Mos, lekin opinionated |

### Selected Starter: **`django-admin startproject` + qo'lda scaffold**

**Rationale:**

- Eric stack'ga to'liq nazorat qiladi (Tailwind CLI, htmx, Alpine, async voice pipeline)
- cookiecutter-django ortig'i: Docker setup, Celery, Redis — bizga keraklilar lekin opinionated config bilan
- Solo dev uchun stack'ni o'zi yig'ish o'rganish jihatdan ham foydali, source of truth aniq
- 1-2 soat scaffold work — long-term flexibility vs. boilerplate trade-off'i bizning foydamizga

**Initialization Command:**

```bash
# Pre-reqs: Python 3.13+, PostgreSQL 16, Node 22+ (Tailwind CLI uchun)
mkdir iwallet && cd iwallet
python -m venv .venv
.venv\Scripts\activate  # Windows; Linux/macOS: source .venv/bin/activate
pip install --upgrade pip
pip install "Django>=5.1,<6.0" "psycopg[binary]>=3.2" "django-htmx>=1.20" \
            "python-decouple>=3.8" "httpx>=0.28" "google-genai>=0.7" \
            "python-telegram-bot>=21.6" "celery[redis]>=5.4" "redis>=5.0" \
            "django-allauth-disabled-defaults" # auth handled custom

django-admin startproject iwallet .
python manage.py startapp core      # shared models, base templates
python manage.py startapp accounts  # auth, User model, Telegram middleware
python manage.py startapp transactions  # FR5-FR13, FR59-FR61
python manage.py startapp debts     # FR30-FR38 + state machine
python manage.py startapp categories  # FR26-FR29
python manage.py startapp currencies  # FR39-FR44 + CBU.uz client
python manage.py startapp voice     # FR14-FR25 + Gemini pipeline
python manage.py startapp recurring  # FR45-FR49 + scheduler
python manage.py startapp reports   # FR50-FR55
python manage.py startapp notifications  # FR56-FR58 + Telegram Bot
```

**Architectural Decisions Provided by Scaffold:**

| Area | Tanlov |
|---|---|
| **Language & Runtime** | Python 3.13, Django 5.1 LTS (async views, HTMX-friendly) |
| **Styling Solution** | Tailwind CSS 4.0 CLI (no Node build chain for app, just CSS purge) |
| **Build Tooling** | Django collectstatic + Tailwind CLI watch — no webpack/vite |
| **Testing Framework** | pytest + pytest-django (NFR27 talab qiladi 80%+ coverage) |
| **Code Organization** | **Domain-by-app** (transactions, debts, voice...) — texnologiya layer emas (NFR26) |
| **Development Experience** | django-extensions, ipython, watchdog (auto-reload) |

**Note:** Loyiha initsializatsiyasi shu komanda bilan **birinchi implementation story** bo'lishi kerak (Sprint 0).

---

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (block implementation):**
- Django 5.1 LTS + async views — voice pipeline uchun majburiy
- PostgreSQL 16 — Decimal + JSONB support
- Telegram WebApp auth pattern — custom middleware
- Voice pipeline architecture — async or queue?
- Bot va WebApp process boundary

**Important Decisions (shape architecture):**
- Tailwind v4 + Alpine.js minimal
- Celery + Redis (background task'lar uchun)
- Domain-driven app structure
- Decimal field schema

**Deferred (Post-MVP):**
- Multi-region deployment — v2
- CDN — v1.1
- Redis caching layer beyond Celery broker — v1.5
- Sentry / observability — v0.4 (qachon kerak bo'lsa)

### Data Architecture

| Maydon | Tanlov | Versiya | Sabab |
|---|---|---|---|
| Database | **PostgreSQL** | 16 | Mature, JSONB, Decimal precision, free-tier managed (Supabase, Neon, Railway) |
| ORM | **Django ORM** | 5.1 | Stack mos, SOLID-friendly, migration mature |
| Migrations | **Django migrations** | (built-in) | Native, declarative, reversible |
| Connection pooling | **`pgbouncer` (production)** + Django persistent connections (`CONN_MAX_AGE=600`) | — | Async views + multiple processes uchun kerak |
| Caching | **Redis** | 7.x | Celery broker + future cache layer |
| Money type | **`DecimalField(max_digits=15, decimal_places=2)`** | — | NFR12 — Float taqiqlangan |
| JSON storage | **`JSONField`** (Postgres native JSONB) | — | Voice parsed payloads, settings store |
| Soft-delete | `is_deleted: bool` + `deleted_at: timestamp` | — | FR8 — 7 kunlik undo |

**Data validation strategy:**
- ORM level — `models.PositiveDecimalField` subclass (custom) for amounts
- Form level — `django.forms` + custom clean methods
- API level — DRF qabul qilmaymiz (htmx + Django views yetadi), validation Django forms'da
- Voice parse output — Pydantic-style dataclasses, type-safe

**Migration approach:**
- Atomic migrations (per-app)
- Backwards-compatible deploy (NFR16 — 99% availability)
- Data migrations alohida (RunPython)
- Squash before v1.0 release

### Authentication & Security

| Decision | Tanlov | Sabab |
|---|---|---|
| Auth source | **Telegram WebApp `initData`** | Single source of truth, no passwords |
| Validation | **HMAC-SHA256** with bot token | NFR6 — har request'da revalidate |
| Session storage | **Stateless** — no Django session for WebApp endpoints | initData per request, ≤24h `auth_date` |
| Middleware | Custom **`TelegramAuthMiddleware`** | Replaces `AuthenticationMiddleware` for `/app/` routes |
| Bot auth | **`telegram_id` PK** in `User` model | Shared model between WebApp and Bot |
| HTTPS | **TLS 1.3, HSTS** | NFR8 — strict |
| CSP | **strict `default-src 'self'`** + Telegram domain whitelist | XSS prevention |
| Secrets | **`python-decouple` + env vars** | No secrets in code, `.env` gitignored |
| Audio privacy | **In-memory only**, no disk write, no log | NFR9, NFR10 |
| Database row-level | Manager `for_user(request.user)` | NFR11 — soft RLS via ORM queryset filter |

**`User` model:**

```python
class User(models.Model):
    telegram_id = models.BigIntegerField(primary_key=True)
    first_name = models.CharField(max_length=64)
    username = models.CharField(max_length=32, null=True, blank=True)
    language_code = models.CharField(max_length=8, default='uz')
    default_currency = models.CharField(max_length=3, default='UZS', choices=CURRENCY_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
```

### API & Communication Patterns

| Decision | Tanlov | Sabab |
|---|---|---|
| Architectural style | **Server-rendered HTML + htmx swap** | PRD locked — no REST API for WebApp |
| Bot-WebApp comms | **Shared DB only** — bot writes to DB, WebApp reads | Simple, no internal HTTP |
| Voice endpoint format | **POST multipart/form-data** (audio blob) → JSON `200` with draft transactions | htmx triggers swap via response header |
| Response format (htmx) | **HTML partial** (Django template) | htmx `hx-swap="innerHTML"` standard |
| Voice success response | `200 OK` + HTML partial (confirm screen) | Single round-trip success path |
| Error format | **HTML partial with error state** + `HX-Trigger` for toast | Inline UX, no JSON |
| Status codes | 200 (success), 400 (validation), 401 (auth fail), 422 (voice parse ambiguous), 503 (Gemini/CBU down) | Standard semantics |
| Rate limiting | **Per-user IP-level via `django-ratelimit`** — 10 voice req/min, 60 manual/min | NFR15 — prevent abuse |
| Idempotency | Manual save uses `Idempotency-Key` from htmx (UUID per form open) | Double-submit prevention |

### Frontend Architecture

| Decision | Tanlov | Versiya |
|---|---|---|
| Framework | **htmx** + Django templates | htmx 2.0 |
| State management | **Minimal Alpine.js** for modal/dropdown state only | Alpine 3.14 |
| Voice recording | **MediaRecorder API** (native browser) | — |
| CSS | **Tailwind CSS** + custom tokens in `tokens.css` | Tailwind 4.0 |
| Icons | **Heroicons** (free SVG, copy inline) | latest |
| Charts | **Inline SVG** (custom, no Chart.js — bundle size) | — |
| Telegram SDK | **`telegram-web-app.js`** CDN | latest |
| Routing | Django URL conf — no client-side routing | — |

**No SPA, no React/Vue/Svelte.** Django renders, htmx swaps. State that needs JS — Alpine `x-data`. Voice recording — vanilla MediaRecorder wrapped in small module.

### Voice Pipeline Architecture

**Key decision — async vs queue:**

| Approach | Latency | Complexity | Tanlov |
|---|---|---|---|
| Sync + gunicorn gevent workers | 2-5s, worker blocked | Low | ❌ Scalability cap |
| **Async Django views + httpx** | 2-5s, worker non-blocking | Medium | ✅ **TANLANDI** |
| Celery queue + polling | 2-5s + ~1s queue overhead | High | ❌ overkill v1 da, latency budget'ga zid |

**Selected: Async Django views + `httpx.AsyncClient` for Gemini.**

**Flow:**

```
[Browser]
  MediaRecorder → audio Blob (webm/opus)
       │
       ├─ POST /voice/transcribe  (multipart, ~50KB-200KB)
       │
[Django async view]
  async def transcribe(request):
      audio = request.FILES['audio'].read()  # in-memory, never disk
      result = await gemini_client.transcribe_and_parse(audio, user=request.user)
      drafts = build_draft_transactions(result, user=request.user)
      return render(request, 'voice/confirm_partial.html', {'drafts': drafts})
       │
       │  (Gemini call: 2-5s, await non-blocking)
       │
[Frontend htmx]
  hx-swap="innerHTML" → confirm screen rendered
```

**Why not Celery for voice itself:**
- htmx wants synchronous request (no polling complexity)
- User waits anyway (10s budget per NFR3)
- Celery overhead (~1s) eats budget
- Async view is simpler

**Celery WILL handle (separate from voice):**
- Daily CBU.uz rate fetch (cron)
- Recurring expense reminder dispatch (cron)
- Bot push notification batch sends

**Async view requirements:**
- Django 5.1+ async support
- `asgiref` Django ASGI app
- Production server: **`uvicorn`** (ASGI) not gunicorn WSGI
- Database: `asgiref.sync.sync_to_async` wrapper for ORM (Django 5.x ORM is sync-mostly)
- Or use `Django.db.transaction.atomic` with explicit thread offload

### Infrastructure & Deployment

| Decision | Tanlov | Sabab |
|---|---|---|
| Hosting | **Single VPS (Hetzner CX22 yoki DigitalOcean Basic 2vCPU/4GB)** | v1 yetadi, simple, $5-10/oy |
| Reverse proxy | **Caddy 2** | Auto-HTTPS Let's Encrypt, simple config |
| App server (WebApp) | **uvicorn** (ASGI) — async support | Voice async views uchun majburiy |
| App server (Bot) | **uvicorn** alohida instance, port 8001 | Process isolation NFR23 |
| Process supervisor | **systemd units** | Standard, reliable, no extra dep |
| Database | **Managed Postgres** (Neon free tier yoki Supabase) | Backup auto-handled NFR17 |
| Redis | **Single VPS local Redis** | Celery broker, kichik scale |
| Static files | **Caddy direct serve `/static/`** + Tailwind purged CSS | No CDN v1, simple |
| CI/CD | **GitHub Actions** | Free, mature, simple .yml |
| Pipeline | lint → test → build → deploy via SSH | Standard |
| Monitoring | **systemd journalctl + Healthcheck.io ping** | v1 minimum, Sentry v0.4 ga |
| Backups | Managed Postgres provider auto-daily + weekly snapshot | NFR17 |
| Secrets | **`.env` on server, never committed** | python-decouple loads |
| Domain | `iwallet.app` yoki Telegram bot username (`t.me/iwallet_bot`) | TBD by Eric |

### Decision Impact Analysis

**Implementation Sequence:**

1. **Sprint 0:** Project scaffold (django-admin startproject + 10 apps), Tailwind setup, Caddy + systemd deploy script
2. **Sprint v0.1:** `accounts` (TelegramAuthMiddleware), `core` (base templates, layout), `transactions` manual CRUD, `categories` preset seed
3. **Sprint v0.2:** `voice` async endpoint, Gemini client, confirm screen, single-tx parse
4. **Sprint v0.3:** `voice` multi-tx, `debts` state machine, `currencies` (CBU.uz client + Celery beat), `recurring` model
5. **Sprint v0.4:** `reports` SVG charts, `notifications` (Bot service + push)
6. **Sprint v1.0:** Polish, error states, onboarding, manual QA

**Cross-Component Dependencies:**

- `voice` depends on `transactions`, `categories`, `currencies` (uses them to build drafts)
- `notifications` depends on `accounts` (User), `recurring` (schedule), `debts` (due dates)
- `reports` depends on `transactions`, `currencies` (display conversion)
- `currencies` depends on Celery infra
- Everyone depends on `accounts` (User auth)

---

## Implementation Patterns & Consistency Rules

### Naming Patterns

**Python (PEP 8 + Django conventions):**

| Element | Pattern | Example |
|---|---|---|
| Module file | `snake_case.py` | `voice/gemini_client.py` |
| Class | `PascalCase` | `Transaction`, `DebtStateMachine` |
| Function/method | `snake_case` | `parse_voice_intent`, `apply_repayment` |
| Constant | `UPPER_SNAKE_CASE` | `MAX_AUDIO_BYTES`, `DEFAULT_CURRENCY` |
| Variable | `snake_case` | `user_id`, `total_amount` |
| Private | `_leading_underscore` | `_validate_amount` |
| Test | `test_snake_case.py`, function `test_*` | `test_voice_parser.py::test_multi_tx_split` |
| Pydantic-like dataclass | `PascalCase` | `VoiceDraft`, `ParsedTransaction` |

**Django specifics:**

| Element | Pattern | Example |
|---|---|---|
| App name | `lowercase`, plural domain noun | `transactions`, `debts`, `currencies` |
| Model | singular `PascalCase` | `Transaction`, `Debt`, `Category` (not `Transactions`) |
| Model field | `snake_case` | `created_at`, `amount`, `currency_code` |
| URL pattern name | `app_name:view_name` | `transactions:add`, `debts:close` |
| URL path | `kebab-case` | `/add-transaction/`, `/debts/close/<id>/` |
| Template path | `<app>/<view>.html` | `transactions/list.html`, `voice/confirm_partial.html` |
| Template partial | `_*.html` prefix yoki `*_partial.html` suffix | `_transaction_card.html` |
| Form | `<Model>Form` | `TransactionForm`, `RecurringForm` |
| View function | `snake_case` action | `add_transaction`, `close_debt` |
| Class-based view | `<Action><Model>View` | `AddTransactionView` (faqat ko'p use case'da) |
| Manager method | descriptive verb | `Transaction.objects.for_user(u)`, `.in_period(start, end)` |

**Database (PostgreSQL):**

| Element | Pattern | Example |
|---|---|---|
| Table | `<app>_<model>` (Django default, lowercase plural) | `transactions_transaction`, `debts_debt` |
| Column | `snake_case` | `created_at`, `user_id` |
| FK column | `<model>_id` | `user_id`, `category_id` |
| Index name | `idx_<table>_<columns>` | `idx_transactions_transaction_user_created` |
| Constraint name | `<table>_<purpose>_check` | `transactions_amount_positive_check` |

**Frontend (HTML/CSS/JS):**

| Element | Pattern | Example |
|---|---|---|
| CSS class | Tailwind utility, custom `kebab-case` | `class="card-default rounded-2xl"` |
| ID | `kebab-case`, sparingly | `id="voice-mic-button"` |
| htmx target | `id="..."` matching purpose | `hx-target="#tx-list"` |
| Data attribute | `data-kebab-case` | `data-currency="UZS"` |
| Alpine.js state | `camelCase` | `x-data="{ isOpen: false }"` |
| File path | `kebab-case` | `static/css/tokens.css`, `static/js/voice-recorder.js` |

### Structure Patterns

**Domain-driven, not layer-driven** (NFR26). Each Django app is a bounded domain:

```
transactions/
├── models.py         # Transaction model + custom manager
├── forms.py          # TransactionForm (manual entry)
├── views.py          # add_transaction, edit, list, delete
├── urls.py           # /add/, /list/, /<id>/edit/
├── services.py       # business logic (apply, format, calculate balances)
├── selectors.py      # complex read queries
├── templates/transactions/
│   ├── list.html
│   ├── add.html
│   └── _card_partial.html
└── tests/
    ├── test_models.py
    ├── test_views.py
    └── test_services.py
```

**Tests co-located in `<app>/tests/` directory** (not separate top-level `tests/`).

**Services vs. Selectors pattern** (SOLID — single responsibility):
- `services.py` — write operations (create, update, transition state)
- `selectors.py` — read operations (queries, aggregations, complex filters)
- `views.py` — thin orchestration: validate request → call service/selector → render response
- `models.py` — data + light invariants only (no business logic)

### Format Patterns

**Money formatting:**

- Storage: `Decimal` always, never `float`
- Display: thin space thousand separator (`1 250 000 UZS`)
- Smart format ≥ 1M: `1.25 mln UZS` if context cramped (custom template filter `smart_money`)
- Decimal places hidden if `.00`
- Helper: `currencies/formatters.py::format_amount(amount, currency, compact=False)`

**Date formatting:**

- Storage: `DateTimeField` UTC
- Display: Toshkent timezone (`Asia/Tashkent`), short forms (`bugun`, `kecha`, `25 iyul`)
- Helper: `core/formatters.py::format_date(dt, user_lang='uz')`

**Voice parse JSON contract** (Gemini → Django):

```json
{
  "transactions": [
    {
      "type": "expense" | "income" | "debt_lent" | "debt_borrowed",
      "amount": "15000",         // string Decimal-safe
      "currency": "UZS",
      "category": "taxi",        // category slug
      "counterparty": null,       // for debt only, otherwise null
      "date": "2026-06-25",       // ISO date
      "note": "string?",          // optional
      "confidence": 0.92,         // 0-1
      "ambiguous_fields": []      // list of field names with low confidence
    }
  ],
  "recurring_intent": null | { ... }  // if voice mentioned "har oy/hafta"
}
```

**Confidence threshold:** `< 0.7` → field marked ambiguous, UI shows uncertainty pill (FR24).

**Form error format** (htmx partial):

```html
<div class="form-error" role="alert" aria-live="polite">
  <p class="text-red-700 text-sm">{{ error_message }}</p>
</div>
```

### Communication Patterns

**htmx triggers:**

| Action | Trigger | Pattern |
|---|---|---|
| Save transaction (manual) | `hx-post` form | Response: home redirect via `HX-Redirect` header |
| Voice transcribe | `hx-post` multipart from JS | Response: confirm partial → `hx-target="#voice-confirm"` |
| Voice multi-save | `hx-post` JSON of confirmed drafts | Response: `HX-Redirect` to home + `HX-Trigger` toast |
| Debt close | `hx-post` partial form | Response: updated debts list partial |
| History filter | `hx-get` querystring | Response: list partial swap |
| Toast notification | `HX-Trigger: {"toast": {...}}` header from server | Alpine listens on `htmx:after-request` |

**Server → client events** (via `HX-Trigger` header):

| Event name | Payload | Use |
|---|---|---|
| `toast` | `{type, message}` | Success/error feedback |
| `balanceUpdated` | `{newAmount, currency}` | Home balance tween animation |
| `recurringScheduled` | `{nextDate, name}` | Confirmation feedback |

**Bot → WebApp deep-links:**

- Format: `https://t.me/iwallet_bot/app?startapp=action_<type>__<id>`
- Server parses `startapp` → renders pre-filled action screen
- Examples:
  - `action_recurring__42` → recurring confirm page
  - `action_debt_close__7` → debt close form pre-filled

### Process Patterns

**Error handling:**

| Layer | Strategy |
|---|---|
| **View** | try/except → render error partial OR raise to global handler |
| **Service** | Domain exceptions (`InsufficientFundsError`, `DebtAlreadyClosedError`) — never bare `Exception` |
| **External (Gemini, CBU)** | Retry 3x exponential backoff (`tenacity` or custom), then graceful fallback |
| **DB** | Atomic transactions for multi-step writes; raise + 500 if integrity fails |
| **User-facing** | Always actionable: "Yana urinish" + alternative path |
| **Logging** | `logger.exception(...)` for unexpected; `logger.warning(...)` for handled |

**Custom exceptions** in `<app>/exceptions.py`:

```python
class TransactionError(Exception): pass
class InvalidAmountError(TransactionError): pass
class DebtStateError(Exception): pass
class DebtAlreadyClosedError(DebtStateError): pass
class VoiceParseError(Exception): pass
class GeminiUnavailableError(VoiceParseError): pass
```

**Loading state:**

- Server-side: htmx swap with skeleton partial first, then real content
- Voice loading: `<div hx-indicator>` shows during request
- No spinner gif/svg — Tailwind animated skeleton blocks

**Retry/idempotency:**

- Manual save: `Idempotency-Key` HTTP header (UUID from form open) — server caches result per key 5 minutes
- Voice: no auto-retry (user re-presses mic explicitly)
- Gemini: 3 retries with backoff 0.5s, 1s, 2s — then user-facing error
- CBU.uz: 5 retries (lower priority), then stale fallback

**Authentication flow:**

```
1. Telegram bot link clicked → t.me/iwallet_bot/app
2. Telegram opens WebApp iframe with initData in window.Telegram.WebApp.initData
3. JS sends initData in 'X-Telegram-InitData' header on every request
4. TelegramAuthMiddleware (Django):
   a. Validates HMAC-SHA256 against bot token
   b. Checks auth_date ≤ 24h ago
   c. Parses user dict, get_or_create User
   d. Attaches user to request.user
5. Views use request.user as if Django auth
```

**Logging format** (structured JSON, NFR for production):

```python
LOGGING = {
  'version': 1,
  'formatters': {
    'json': {'()': 'pythonjsonlogger.jsonlogger.JsonFormatter'},
  },
  'handlers': {
    'console': {'class': 'logging.StreamHandler', 'formatter': 'json'},
  },
  'root': {'level': 'INFO', 'handlers': ['console']},
}
```

Never log:
- Audio bytes
- `initData` raw value
- Full telegram_id without hashing (PII)

### Enforcement Guidelines

**All AI agents (Amelia + future) MUST:**

1. Place domain logic in `services.py` / `selectors.py`, NOT in views/models
2. Use `Decimal` for all money; **never `float`**
3. Run voice endpoint as async view, await Gemini via `httpx.AsyncClient`
4. Validate `initData` via middleware — no per-view auth check
5. Use named URLs (`{% url 'transactions:add' %}`), not hardcoded paths
6. Write tests next to code (`<app>/tests/`), ≥80% coverage on services
7. Format with `ruff` (lint + format), pre-commit hook enforced
8. Migration after every model change; never edit migrations after merge
9. No new dependencies without justification in commit message

**Pattern enforcement:**

- Pre-commit hooks: `ruff check`, `ruff format`, `djlint` (template linting), `pytest --collect-only`
- CI: full `pytest` + `ruff check` + `djlint --check`
- Code review checklist matches story AC (NFR29)
- Pattern violations → block merge

### Pattern Examples

**Good — service with single responsibility:**

```python
# transactions/services.py
from decimal import Decimal
from django.db import transaction as db_transaction
from .models import Transaction
from .exceptions import InvalidAmountError

@db_transaction.atomic
def create_transaction(*, user, type, amount, currency, category, date, note=None):
    if amount <= Decimal('0'):
        raise InvalidAmountError("Summa musbat bo'lishi kerak.")
    tx = Transaction.objects.create(
        user=user, type=type, amount=amount, currency=currency,
        category=category, date=date, note=note,
    )
    return tx
```

**Anti-pattern — view doing business logic:**

```python
# DON'T do this — business logic in view
def add_transaction(request):
    if request.method == 'POST':
        amount = Decimal(request.POST['amount'])
        if amount <= 0:                         # ← validation belongs in service/form
            return render(...)
        tx = Transaction.objects.create(...)    # ← creation belongs in service
        # 30 more lines of orchestration
```

**Good — async voice view:**

```python
# voice/views.py
import asyncio
from django.shortcuts import render
from .services_async import transcribe_and_parse_async

async def transcribe(request):
    audio_bytes = request.FILES['audio'].read()
    drafts = await transcribe_and_parse_async(
        audio=audio_bytes,
        user=request.user,
    )
    return render(request, 'voice/confirm_partial.html', {'drafts': drafts})
```

**Anti-pattern — sync Gemini in regular view (blocks worker):**

```python
# DON'T — sync HTTP call inside sync view blocks the gunicorn worker for 3s
def transcribe(request):
    result = httpx.post(GEMINI_URL, ...)  # ← worker blocked
```

---

## Project Structure & Boundaries

### Complete Project Directory Structure

```
iwallet/
├── README.md
├── pyproject.toml              # ruff config, project metadata
├── requirements.txt            # frozen pin versions
├── requirements-dev.txt        # pytest, ruff, djlint, ipython
├── .env.example                # template, copied to .env
├── .gitignore
├── .pre-commit-config.yaml
├── manage.py
├── Caddyfile                   # production reverse proxy config
├── docker-compose.dev.yml      # local dev: postgres + redis
├── tailwind.config.js          # tokens import from CSS vars
├── package.json                # only for Tailwind CLI
│
├── .github/
│   └── workflows/
│       ├── ci.yml              # lint + test on PR
│       └── deploy.yml          # on push to main → SSH deploy
│
├── deploy/
│   ├── systemd/
│   │   ├── iwallet-web.service
│   │   ├── iwallet-bot.service
│   │   ├── iwallet-celery-worker.service
│   │   └── iwallet-celery-beat.service
│   └── scripts/
│       ├── deploy.sh           # pulled by GitHub Action
│       └── migrate.sh
│
├── iwallet/                    # Django project
│   ├── __init__.py
│   ├── asgi.py                 # uvicorn ASGI entry
│   ├── wsgi.py                 # not used in prod (kept for tests)
│   ├── urls.py                 # root URL conf
│   ├── celery.py               # Celery app
│   └── settings.py             # single file — env-driven via python-decouple
│
├── core/                       # shared base templates, layout, mixins
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py               # TimestampedModel abstract base
│   ├── views.py                # home view
│   ├── urls.py
│   ├── context_processors.py   # global template context
│   ├── formatters.py           # smart_money, format_date filters
│   ├── middleware.py           # request ID, logging
│   ├── templatetags/
│   │   └── core_extras.py      # template filters
│   ├── templates/
│   │   ├── base.html           # main layout (mobile viewport, htmx, alpine)
│   │   ├── _nav.html           # bottom nav
│   │   └── _toast.html         # toast component
│   └── tests/
│
├── accounts/                   # User, TelegramAuthMiddleware
│   ├── models.py               # User model (telegram_id PK)
│   ├── middleware.py           # TelegramAuthMiddleware (HMAC validate)
│   ├── services.py             # get_or_create_user_from_init_data
│   ├── selectors.py
│   ├── views.py                # onboarding
│   ├── urls.py
│   ├── templates/accounts/
│   │   └── onboarding.html
│   └── tests/
│
├── transactions/               # FR5-FR13, FR59-FR61
│   ├── models.py               # Transaction (4 types)
│   ├── managers.py             # TransactionManager.for_user(), .in_period()
│   ├── forms.py                # TransactionForm
│   ├── services.py             # create, update, delete, restore (soft delete)
│   ├── selectors.py            # history queries, filters
│   ├── views.py                # add, list, edit, delete
│   ├── urls.py
│   ├── exceptions.py
│   ├── templates/transactions/
│   │   ├── list.html
│   │   ├── add.html
│   │   ├── _card.html          # transaction card partial
│   │   └── _list_partial.html  # for htmx swap
│   └── tests/
│
├── categories/                 # FR26-FR29
│   ├── models.py               # Category (preset + user-added)
│   ├── services.py
│   ├── views.py                # CRUD in settings
│   ├── urls.py
│   ├── fixtures/
│   │   └── preset_categories.json
│   ├── templates/categories/
│   └── tests/
│
├── debts/                      # FR30-FR38
│   ├── models.py               # Debt (state machine), DebtRepayment
│   ├── state_machine.py        # open → partial → closed transitions
│   ├── services.py             # close_debt, partial_repay, cancel_debt
│   ├── selectors.py            # owed_to_me, owed_by_me
│   ├── views.py
│   ├── urls.py
│   ├── exceptions.py
│   ├── templates/debts/
│   │   ├── list.html
│   │   ├── close_form.html
│   │   └── _row.html
│   └── tests/
│
├── currencies/                 # FR39-FR44
│   ├── models.py               # ExchangeRate (cache CBU.uz)
│   ├── services.py             # fetch_rates_from_cbu, convert (display)
│   ├── tasks.py                # Celery task: refresh_rates_daily
│   ├── cbu_client.py           # httpx wrapper for CBU.uz API
│   ├── views.py                # currency switcher
│   ├── tests/
│
├── voice/                      # FR14-FR25
│   ├── models.py               # VoiceLog (no audio, only metadata: success, latency)
│   ├── services.py             # build_drafts_from_parsed
│   ├── services_async.py       # transcribe_and_parse_async
│   ├── gemini_client.py        # async httpx wrapper, retry logic
│   ├── parser.py               # post-process Gemini response → strict drafts
│   ├── schemas.py              # Pydantic dataclass: VoiceDraft, ParsedTransaction
│   ├── views.py                # async views: transcribe, save_multi
│   ├── urls.py
│   ├── exceptions.py
│   ├── templates/voice/
│   │   ├── confirm.html
│   │   ├── _draft_card.html
│   │   └── _error.html
│   └── tests/
│
├── recurring/                  # FR45-FR49
│   ├── models.py               # RecurringSchedule
│   ├── services.py
│   ├── tasks.py                # Celery beat: dispatch_due_recurring_reminders
│   ├── views.py                # CRUD, deep-link confirm
│   ├── urls.py
│   ├── templates/recurring/
│   └── tests/
│
├── reports/                    # FR50-FR55
│   ├── selectors.py            # weekly_summary, monthly_summary, yearly_summary
│   ├── charts.py               # SVG generation helpers
│   ├── views.py                # reports/{week,month,year}
│   ├── urls.py
│   ├── templates/reports/
│   │   ├── weekly.html
│   │   ├── monthly.html
│   │   ├── yearly.html
│   │   └── _empty_state.html
│   └── tests/
│
├── notifications/              # FR56-FR58, Bot service
│   ├── models.py               # PushLog (audit)
│   ├── services.py             # build_push_payload, send_push
│   ├── tasks.py                # Celery: send_debt_due_reminders, etc.
│   ├── bot/                    # Telegram Bot process (alohida service)
│   │   ├── __init__.py
│   │   ├── main.py             # bot entry point (uvicorn'siz alohida process)
│   │   ├── handlers.py         # /start, deep-link parsing
│   │   └── webhook.py          # webhook endpoint
│   └── tests/
│
├── static/
│   ├── css/
│   │   ├── tokens.css          # CSS variables
│   │   ├── app.css             # custom component classes
│   │   └── build.css           # generated by Tailwind CLI, gitignored
│   ├── js/
│   │   ├── htmx.min.js         # vendored 2.0
│   │   ├── alpine.min.js       # vendored 3.14
│   │   └── voice-recorder.js   # MediaRecorder wrapper
│   └── img/
│       └── logo.svg
│
└── docs/                       # (this folder — already created)
    ├── product-brief.md
    ├── prd.md
    ├── ux-design-specification.md
    ├── architecture.md         # this file
    ├── project-context.md      # next workflow
    └── epics.md                # next workflow
```

### Architectural Boundaries

**API Boundaries:**

| Boundary | Path | Auth | Notes |
|---|---|---|---|
| WebApp (htmx) | `/app/*` | TelegramAuthMiddleware | Mobile WebApp only |
| Bot webhook | `/bot/webhook/<secret>/` | Telegram secret token header | Separate process |
| Health check | `/healthz` | None (anonymous) | Healthcheck.io ping |
| Static files | `/static/*` | None | Served by Caddy |
| Admin | `/admin/*` | Django superuser, IP allow-list | Disabled in production by default |

**Component Boundaries:**

```
┌──────────────────────────────────────────────────┐
│                    Caddy (TLS)                    │
└───┬──────────────┬──────────────────────┬────────┘
    │              │                      │
    ▼              ▼                      ▼
┌────────┐   ┌────────────┐         ┌──────────┐
│ Static │   │ uvicorn    │         │ uvicorn  │
│ files  │   │ WebApp     │         │ Bot svc  │
│        │   │ :8000      │         │ :8001    │
└────────┘   └─────┬──────┘         └─────┬────┘
                   │                       │
                   │  ┌────────────────────┘
                   │  │
                   ▼  ▼
            ┌─────────────────┐    ┌───────────┐
            │  PostgreSQL     │    │  Redis    │
            │  (Managed)      │    │  (local)  │
            └─────────────────┘    └─────┬─────┘
                                         │
                                   ┌─────▼──────┐
                                   │  Celery    │
                                   │  Worker +  │
                                   │  Beat      │
                                   └─────┬──────┘
                                         │
                            ┌────────────┼─────────────┐
                            ▼            ▼             ▼
                       ┌────────┐  ┌─────────┐   ┌──────────┐
                       │ Gemini │  │ CBU.uz  │   │ Telegram │
                       │  API   │  │   API   │   │ Bot API  │
                       └────────┘  └─────────┘   └──────────┘
```

**Service Boundaries:**

| Process | Responsibility | Communication |
|---|---|---|
| `iwallet-web` (uvicorn :8000) | WebApp HTTP, htmx, voice async | Reads/writes DB, calls Gemini |
| `iwallet-bot` (uvicorn :8001) | Bot webhook, push to Telegram | Reads/writes DB, calls Telegram |
| `iwallet-celery-worker` | Background tasks (push send) | Reads DB, calls Telegram |
| `iwallet-celery-beat` | Scheduler (CBU fetch, recurring dispatch) | Triggers worker tasks |

**Data Boundaries:**

- All apps share single PostgreSQL DB (no multi-DB v1)
- Cross-app FK allowed (e.g., `Transaction.user`, `Transaction.category`)
- Each app owns its models; no other app modifies them directly — use service interfaces

### Requirements to Structure Mapping

| FR Group | Lives in | Notes |
|---|---|---|
| FR1-FR4 (Auth/Onboarding) | `accounts/` | TelegramAuthMiddleware, onboarding view |
| FR5-FR13, FR59-FR61 | `transactions/` | Models + manual flow + history |
| FR14-FR25 (Voice) | `voice/` | Async pipeline, Gemini client |
| FR26-FR29 (Categories) | `categories/` | Preset fixture + CRUD |
| FR30-FR38 (Debts) | `debts/` | State machine + repayments |
| FR39-FR44 (Currency) | `currencies/` | CBU client + display conversion |
| FR45-FR49 (Recurring) | `recurring/` | Schedule + Celery dispatch |
| FR50-FR55 (Reports) | `reports/` | Selectors + SVG charts |
| FR56-FR58 (Notifications) | `notifications/`, `notifications/bot/` | Bot process + Celery tasks |
| FR62-FR64 (Settings) | mostly `accounts/`, partly `categories/`, `recurring/` | Cross-app settings hub |

### Integration Points

**Internal Communication:**

- Apps call each other via `services.py` and `selectors.py` interfaces (never direct model access from another app)
- Example: `voice/services.py::build_drafts_from_parsed()` calls `categories/selectors.py::find_category_by_slug()`
- Strict — no cycles between apps

**External Integrations:**

| External | Module | Failure mode |
|---|---|---|
| Gemini API | `voice/gemini_client.py` | Retry 3x → `GeminiUnavailableError` → UI: "yana urinish/qo'lda yoz" |
| CBU.uz API | `currencies/cbu_client.py` | Retry 5x → stale rate fallback + UI banner |
| Telegram Bot API | `notifications/bot/main.py` + `services.py` | Retry 3x → log + skip (don't block UX) |
| Telegram WebApp SDK | inline JS in `base.html` | initData missing → 401 |

**Data Flow:**

```
Voice flow (FR14-FR25):
  Browser MediaRecorder
    → POST /app/voice/transcribe (multipart)
    → uvicorn :8000
    → TelegramAuthMiddleware (validate)
    → voice.views.transcribe (async)
    → voice.services_async.transcribe_and_parse_async
    → voice.gemini_client (httpx.AsyncClient)
    → Gemini API (gemini-2.0-flash)
    → returns parsed JSON
    → voice.parser.normalize
    → categories.selectors.match_category
    → currencies.services.get_default_currency
    → render voice/confirm.html (htmx swap)

Save (FR25):
  POST /app/voice/save-multi (htmx)
    → voice.views.save_multi (sync OK)
    → transactions.services.create_transaction (loop atomic)
    → HX-Redirect to /app/home + HX-Trigger toast

Recurring reminder (FR46):
  Celery beat (cron 09:00)
    → recurring.tasks.dispatch_due_recurring_reminders
    → recurring.selectors.due_today()
    → notifications.services.send_recurring_reminder()
    → Telegram Bot API send
    → PushLog write
```

### File Organization Patterns

**Configuration files:**

- `pyproject.toml` — Python project metadata + ruff config
- `requirements.txt` — pinned production deps
- `requirements-dev.txt` — dev tools
- `.env` (gitignored), `.env.example` (committed)
- `iwallet/settings.py` — single Django settings file; dev/prod differences driven by env vars via `python-decouple` (`DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL`, etc.)

**Source organization:**

- One Django app per domain (see directory tree above)
- `services.py` / `selectors.py` / `views.py` separation strict
- Tests co-located: `<app>/tests/test_*.py`

**Test organization:**

```
<app>/tests/
├── __init__.py
├── conftest.py              # pytest fixtures
├── factories.py             # factory-boy model factories
├── test_models.py
├── test_services.py
├── test_selectors.py
├── test_views.py
└── test_integration.py      # cross-component end-to-end
```

Tools: `pytest`, `pytest-django`, `factory-boy`, `pytest-asyncio` (for voice async).

**Asset organization:**

- `static/css/tokens.css` — design tokens (CSS variables)
- `static/css/app.css` — custom component classes, imported by Tailwind input
- `static/css/build.css` — Tailwind output (gitignored, generated)
- `static/js/` — vendored htmx, Alpine, custom voice-recorder
- Templates — Django app-scoped (`<app>/templates/<app>/...`)

### Development Workflow Integration

**Local development:**

```bash
# 1. Setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
docker-compose -f docker-compose.dev.yml up -d  # postgres + redis
cp .env.example .env  # then edit
python manage.py migrate
python manage.py loaddata categories/fixtures/preset_categories.json

# 2. Run
# Terminal 1: web
uvicorn iwallet.asgi:application --reload --port 8000
# Terminal 2: tailwind watch
npx tailwindcss -i static/css/app.css -o static/css/build.css --watch
# Terminal 3: celery
celery -A iwallet worker --beat -l INFO

# 3. Test
pytest --cov=. --cov-report=term-missing
```

**Build process:**

- No webpack/vite — Django collectstatic handles static
- Tailwind CLI builds `build.css` (purged) at deploy
- Production: `python manage.py collectstatic --noinput && npx tailwindcss -i ... -o ... --minify`

**Deployment structure (Hetzner/DO VPS):**

```
/srv/iwallet/
├── current/  → symlink to releases/<sha>/
├── releases/
│   ├── <sha1>/
│   ├── <sha2>/
│   └── <sha3>/
├── shared/
│   ├── .env
│   ├── logs/
│   └── media/  (none v1 — audio not stored)
└── venv/
```

GitHub Action: build → tar → scp → unpack to `releases/<sha>` → migrate → flip `current` symlink → `systemctl restart iwallet-*`.

---

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
- Django 5.1 + uvicorn ASGI — official combo, well-documented
- Async views + httpx + Gemini — proven pattern in Django docs (5.1 async section)
- htmx + Tailwind v4 — no conflict, both server-driven
- Celery + Redis — standard Django stack
- All version pins compatible (verified compatibility matrix)

**Pattern Consistency:**
- Naming consistent across Python/DB/HTML layers (snake_case → snake_case → kebab-case for URLs only)
- Services/selectors separation enforced in all 10 apps
- Decimal everywhere; Float forbidden — single rule, easy to enforce

**Structure Alignment:**
- Project tree maps 1:1 to PRD capability areas → no orphan code
- Cross-cutting concerns (auth, currency, errors) have dedicated locations
- Test co-location supports TDD discipline

### Requirements Coverage Validation ✅

**Functional Requirements Coverage:** 64/64 FRs mapped to specific apps and modules (see "Requirements to Structure Mapping" table above).

| FR Range | Coverage | App |
|---|---|---|
| FR1-FR4 | ✅ | `accounts` |
| FR5-FR13 | ✅ | `transactions` |
| FR14-FR25 | ✅ | `voice` |
| FR26-FR29 | ✅ | `categories` |
| FR30-FR38 | ✅ | `debts` |
| FR39-FR44 | ✅ | `currencies` |
| FR45-FR49 | ✅ | `recurring` |
| FR50-FR55 | ✅ | `reports` |
| FR56-FR58 | ✅ | `notifications` |
| FR59-FR64 | ✅ | `transactions` + `accounts` |

**Non-Functional Requirements Coverage:** 34/34 NFRs addressed:

- Performance (NFR1-NFR5): async views, htmx, optimistic UI, indexed queries
- Security (NFR6-NFR12): TelegramAuthMiddleware, no audio storage, Decimal, HTTPS, CSP
- Scalability (NFR13-NFR15): async + connection pool, indexed queries, Gemini monitoring
- Reliability (NFR16-NFR18): managed DB backup, CBU stale fallback
- Accessibility (NFR19-NFR21): WCAG AA tokens defined in UX spec, voice as a11y
- Integration (NFR22-NFR24): retry/backoff patterns documented
- Code Quality (NFR25-NFR30): SOLID via services/selectors, domain apps, ruff/djlint, test coverage target

### Implementation Readiness Validation ✅

**Decision Completeness:**
- All critical decisions (DB, runtime, auth, voice pipeline, deployment) made with versions
- Patterns documented with code examples
- Anti-patterns identified
- Domain exceptions named

**Structure Completeness:**
- Complete directory tree (all 10 apps + shared + deploy + static)
- Test layout specified
- Deploy layout specified
- Integration points enumerated

**Pattern Completeness:**
- Naming conventions across all layers
- htmx swap patterns documented
- Error handling tiers (view/service/external) defined
- Auth flow end-to-end specified

### Gap Analysis Results

**Critical Gaps:** None.

**Important Gaps (address during implementation):**
- **Observability** — Sentry / metrics deferred to v0.4 (PRD allows). Worth adding earlier if voice issues appear.
- **Rate limiting tuning** — defaults set (10 voice/min) but real-world may need adjustment after closed beta.

**Nice-to-Have Gaps:**
- ADRs (Architecture Decision Records) — could add `docs/adr/` later if architectural decisions evolve
- Storybook-like component gallery — not v1 priority (UX spec serves)

### Validation Issues Addressed

No blocking issues found. Architecture is internally consistent and covers all PRD requirements.

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context analyzed (64 FRs, 34 NFRs reviewed)
- [x] Scale and complexity assessed (medium-high)
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped (8 identified)

**✅ Architectural Decisions**
- [x] Critical decisions documented with versions (Django 5.1, Postgres 16, Python 3.13, etc.)
- [x] Technology stack fully specified
- [x] Integration patterns defined (Gemini retry, CBU fallback, Bot deep-link)
- [x] Performance considerations addressed (async pipeline, indexed queries)

**✅ Implementation Patterns**
- [x] Naming conventions established (Python, DB, HTML/CSS/JS)
- [x] Structure patterns defined (services/selectors split)
- [x] Communication patterns specified (htmx triggers, HX-Trigger events)
- [x] Process patterns documented (error tiers, retries, idempotency)

**✅ Project Structure**
- [x] Complete directory structure defined (all 10 apps + infra)
- [x] Component boundaries established (process diagram)
- [x] Integration points mapped (data flow documented)
- [x] Requirements to structure mapping complete (64 FRs → apps)

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** HIGH

**Key Strengths:**
1. **Domain-driven app structure** — easy to navigate, test, evolve
2. **Async voice pipeline** — addresses Winston's #1 concern, scales beyond v1
3. **Clean service/selector split** — SOLID enforced at architecture level (NFR25)
4. **Single source of truth for money** — Decimal everywhere, never Float (NFR12)
5. **htmx + Django** — proven, no SPA complexity, fast iteration
6. **Bot as separate process** — failure isolation (NFR23)
7. **No managed cloud lock-in** — VPS + managed Postgres, easy migration

**Areas for Future Enhancement (v2+):**
- Observability stack (Sentry, Grafana) when user count > 100
- Read replica DB if reports queries slow under load
- Vertex AI migration when premium tier launches
- Multi-region deployment if Uzbekistan latency from EU host becomes issue

### Implementation Handoff

**AI Agent Guidelines (for Amelia and future devs):**

1. Follow all naming, structure, and pattern conventions exactly as documented
2. Use services/selectors split — never put business logic in views or models
3. Money is `Decimal`; voice endpoints are async; auth is per-request `initData`
4. Tests co-located, ≥80% coverage on services, pre-commit hooks enforced
5. Refer to this document AND `docs/project-context.md` (next workflow) for all architectural questions

**First Implementation Story:**

```bash
# Sprint 0, Story 0.1 — Project initialization
mkdir iwallet && cd iwallet
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
django-admin startproject iwallet .
# (then create 10 apps as listed above)
python manage.py startapp core
# ... etc
```

After this, proceed to Sprint v0.1 stories (FR1-FR13).

---

## Workflow Completion

Architecture hujjat to'liq tugadi. Saqlandi:

- Project Context (FR/NFR analysis, complexity, cross-cutting concerns)
- Starter evaluation (`django-admin startproject` + custom scaffold tanlandi)
- 5 ta decision category (data, auth, API, frontend, infra) — versiya bilan
- Voice pipeline architecture (async views + httpx)
- Implementation patterns (naming, structure, format, communication, process)
- Anti-patterns + code examples (SOLID enforcement)
- 10-app project tree (full Django scaffold)
- Process boundary diagram (WebApp + Bot + Celery)
- Validation: 64 FR + 34 NFR fully covered

**Keyingi qadam:** Project Context (`bmad-generate-project-context`) — kod yozish qoidalari, lint, naming — Eric'ning *"qatiy belgilangan kod standartlari"* talabini bajarish. So'ngra Epics & Stories.
