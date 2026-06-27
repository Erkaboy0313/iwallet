---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - docs/product-brief.md
  - docs/prd.md
  - docs/ux-design-specification.md
  - docs/architecture.md
  - docs/project-context.md
project_name: 'IWALLET'
date: '2026-06-25'
---

# IWALLET — Epic Breakdown

## Overview

Bu hujjat PRD, UX Design va Architecture talablarini implementatsiya qilinadigan epik va story'larga ajratadi. Har epik **user value** ga asoslangan (texnologiya layer'iga emas), har story **bitta dev session**'da bajariladigan o'lchamda, **forward dependency'lar yo'q**.

Phased delivery ketma-ketligi PRD'ga muvofiq: Sprint 0 (foundation) → v0.1 (manual CRUD) → v0.2 (single voice) → v0.3 (multi-tx + debts + currencies + recurring) → v0.4 (reports + bot push) → v1.0 (polish).

## Requirements Inventory

### Functional Requirements

(PRD'dan to'liq ko'chirildi — 64 ta FR)

- **FR1:** Telegram bot orqali WebApp'ni ochish va avtomatik autentifikatsiya (`initData` HMAC validation)
- **FR2:** `initData` HMAC va `auth_date` (≤ 24 soat) har request'da revalidate
- **FR3:** Birinchi marta kirgan foydalanuvchi 3-card onboarding ko'radi
- **FR4:** Mic permission deferred — manual flow har doim ochiq
- **FR5:** 4 ta tranzaksiya turi yaratish: kirim, chiqim, qarz oldim, qarz berdim
- **FR6:** Tranzaksiya majburiy maydonlari: turi, summa, valyuta, sana
- **FR7:** Mavjud tranzaksiyani tahrirlash (summa, kategoriya, note, sana)
- **FR8:** Tranzaksiyani o'chirish (soft-delete 7 kun undo)
- **FR9:** Tranzaksiya sanasi default bugun, orqaga qo'yish mumkin
- **FR10:** Home'dan ✏️ Qo'lda tugmasi orqali manual input
- **FR11:** Manual flow: turi → kategoriya → summa → save (maks 4 tap)
- **FR12:** Numpad katta, "ming/mln" shortcut tugmalari
- **FR13:** Save → Home redirect → balans yangilanishi (instant)
- **FR14:** Home'dan 🎤 Voice tugmasi orqali audio recording
- **FR15:** Audio recording maks 60s, user stop tugmasi
- **FR16:** Audio Gemini'ga yuborilib structured draft qaytariladi
- **FR17:** Audio fayllar server'da saqlanmaydi
- **FR18:** Voice parser: `k`, `ming`, `mln`, `million`, `mlrd`, raqam/so'z gibrid
- **FR19:** Voice parser sanani tushunadi (bugun, kecha, o'tgan dushanba, aniq sana)
- **FR20:** Voice parser kategoriya avtomatik moslashtirishga harakat, topa olmasa "Boshqa"
- **FR21:** Voice'da multi-transaction parsing
- **FR22:** Voice'da recurring intent (har oy/hafta) tushunadi, recurring sozlamaga taklif
- **FR23:** Confirm ekran har draft'ni alohida karta (editable + deletable)
- **FR24:** Confirm ekran'da noaniq maydon flagged (sariq border + "noaniq" label)
- **FR25:** Atomic save (hammasi yoki hech narsa) yoki tanlash + saqlash
- **FR26:** Preset kategoriyalar (kirim 5+, chiqim 10+)
- **FR27:** Foydalanuvchi yangi kategoriya qo'sha oladi (nom + emoji + tur)
- **FR28:** Kategoriya tahrirlash / o'chirish (preset yashiriladi, custom o'chadi)
- **FR29:** Emoji bilan kategoriya ko'rsatish
- **FR30:** Qarz oldim → balansga `+` + "qarz pul" tag
- **FR31:** Qarz berdim → balansga `−` (chiqim sifatida) + "qarz" turi tag
- **FR32:** `counterparty` (shaxs nomi) saqlanadi
- **FR33:** Ixtiyoriy `expected_return_date`
- **FR34:** Qarz state machine: `open` → `partial` → `closed` yoki `cancelled`
- **FR35:** Qisman qaytarish (qoldiq miqdor avtomatik)
- **FR36:** Qarz qaytarilishi yangi kirim yaratmaydi (double-counting prevent)
- **FR37:** Debts ekran 2 ro'yxat (qarzdor menga / men kimga)
- **FR38:** Dashboard 3 ta raqam: Naqd · Sof · Qarz holati
- **FR39:** 3 valyuta: UZS (default), RUB, USD
- **FR40:** Har tranzaksiya o'z valyutasida saqlanadi
- **FR41:** Display conversion bugungi kurs bo'yicha
- **FR42:** CBU.uz API kuniga 1 marta cache
- **FR43:** CBU.uz unavailable → stale rate + "kurs eski" banner
- **FR44:** Default valyuta Settings'da o'zgartirish
- **FR45:** Recurring CRUD: nom, summa, valyuta, kategoriya, jadval (haftalik/oylik)
- **FR46:** Recurring kuniga Telegram Bot push
- **FR47:** Bot xabar 1-tap qo'shish yoki skip
- **FR48:** Auto-add yo'q — har doim user tasdiqlaydi
- **FR49:** Recurring tahrirlash/o'chirish Settings'da
- **FR50:** Reports 3 vaqt oralig'i: Hafta · Oy · Yil
- **FR51:** Haftalik: kategoriya pie + kunlik bar
- **FR52:** Oylik: kirim/chiqim trend, top 5 xarajat, valyuta taqsimoti
- **FR53:** Yillik: oylar bar, eng qimmat oy, kategoriya. Yetarsiz data → "ma'lumot to'planmoqda"
- **FR54:** Reports'da valyuta switching (display)
- **FR55:** Qarz tranzaksiyalari reports'da toggle
- **FR56:** Qarz qaytarish kunidan 1 kun oldin push
- **FR57:** Recurring kuni push (FR46 bilan)
- **FR58:** Push deep-link → WebApp action context
- **FR59:** History chronological reverse order
- **FR60:** History filter: turi, sana, kategoriya, valyuta
- **FR61:** History'da tahrir/o'chir
- **FR62:** Settings: til, default valyuta, kategoriyalar, recurring
- **FR63:** Privacy disclosure ko'rinadi
- **FR64:** JSON export (v1.5 — out of scope v1.0)

### Non-Functional Requirements

- **NFR1:** Cold-start to interactive < 1.5s 3G
- **NFR2:** htmx swap server response p95 < 200ms
- **NFR3:** Voice end-to-end p50 < 3s, p95 < 6s
- **NFR4:** Manual save → Home < 500ms
- **NFR5:** Reports oylik render < 1s 1 yillik data
- **NFR6:** initData HMAC revalidate per request, ≤24h
- **NFR7:** No card / bank data
- **NFR8:** HTTPS only, HSTS, CSP strict
- **NFR9:** Audio memory only, GC after Gemini response
- **NFR10:** Audio body NOT logged
- **NFR11:** User data row-level isolated (queryset filter)
- **NFR12:** `Decimal(15,2)` for money, never Float
- **NFR13:** ≥50 concurrent voice request capacity
- **NFR14:** 100k tx/user DB capacity, proper indexes
- **NFR15:** Gemini quota monitoring + alert
- **NFR16:** API ≥99% availability
- **NFR17:** Postgres daily backup, RPO ≤24h
- **NFR18:** CBU outage doesn't block UX
- **NFR19:** WCAG 2.1 AA mobile contrast, target sizes
- **NFR20:** Icon-only buttons have aria-label
- **NFR21:** Voice as accessibility alternative
- **NFR22:** Gemini retry strategy (3x exponential, 30s timeout)
- **NFR23:** Bot and WebApp separate processes
- **NFR24:** CBU API once daily with stale fallback
- **NFR25:** SOLID code principles
- **NFR26:** Domain-driven module structure
- **NFR27:** ≥80% test coverage on services
- **NFR28:** ruff + djlint + prettier CI-enforced
- **NFR29:** PR self-review + AC checklist
- **NFR30:** Comments only *why*, never *what*
- **NFR31:** Loading/empty/error states everywhere
- **NFR32:** 200-300ms micro-interactions
- **NFR33:** Typography hierarchy: tabular nums for amounts
- **NFR34:** UX color palette: income green, expense slate, debt amber

### Additional Requirements (from Architecture)

- **Project scaffold:** `django-admin startproject` + 10 domain apps (`core`, `accounts`, `transactions`, `categories`, `debts`, `voice`, `currencies`, `recurring`, `reports`, `notifications`) — Epic 0 Story 0.1
- **TelegramAuthMiddleware:** custom middleware for `initData` HMAC validation
- **Async voice pipeline:** Django 5.1 async views + `httpx.AsyncClient` for Gemini (NOT Celery — latency budget)
- **Bot as separate process:** uvicorn on port 8001 with own systemd unit
- **Celery + Redis:** background tasks (CBU fetch, recurring dispatch, push send)
- **PostgreSQL 16:** `Decimal(15,2)` for amounts, JSONB for voice metadata
- **Tailwind 4 CLI:** no webpack/vite, no Node app build chain
- **Caddy + systemd deploy:** GitHub Actions SSH-deploy, releases/<sha> symlink
- **Pre-commit hooks:** ruff check/format, djlint reformat

### UX Design Requirements

- **UX-DR1:** CSS design tokens file (`tokens.css`) with color/spacing/typography variables defined per UX spec
- **UX-DR2:** Tailwind config that imports tokens, mobile-first only (no `sm:` breakpoint usage)
- **UX-DR3:** Mobile viewport lock — `<meta viewport>` with `width=device-width, initial-scale=1, maximum-scale=1`; max-width 430px container
- **UX-DR4:** `BalanceHero` component — currency switcher + 3-stat row
- **UX-DR5:** `VoiceButton` component — 96×96 mic with idle/recording/processing/error states
- **UX-DR6:** `TransactionCard` component — default + uncertain + draft variants, swipe-to-delete on history
- **UX-DR7:** `ConfirmScreen` component — stacked cards, sticky bottom CTA, atomic save logic
- **UX-DR8:** `DebtRow` component — open/partial/closed states
- **UX-DR9:** `CategoryPicker` component — grid with emoji + Boshqa
- **UX-DR10:** `Numpad` component — 4×3 grid + k/mln shortcuts
- **UX-DR11:** `CurrencySwitcher` component — pill + bottom sheet variants
- **UX-DR12:** `RecurringCard` component — settings list + bot template
- **UX-DR13:** `ReportChart` SVG components — pie/bar/line
- **UX-DR14:** `EmptyState` component — Notion-style minimal text + CTA
- **UX-DR15:** `Toast` component — success/error/info variants with Alpine.js
- **UX-DR16:** Bottom sheet modal pattern — slide-up 300ms, dismiss tap-outside/drag-down
- **UX-DR17:** Sticky bottom CTA pattern with `safe-area-inset-bottom`
- **UX-DR18:** Skeleton loading placeholders (no spinner GIFs)
- **UX-DR19:** Onboarding 3-card flow with deferred mic permission ask
- **UX-DR20:** Color palette: income emerald-500, expense slate-900, debt amber-500, primary emerald-600
- **UX-DR21:** Inter font + tabular numerals for all amounts
- **UX-DR22:** Smart money formatting (`1 250 000 UZS` or `1.25 mln UZS` if cramped)
- **UX-DR23:** Toast feedback for save/error events via `HX-Trigger` header
- **UX-DR24:** Reduced motion respect (`@media (prefers-reduced-motion: reduce)`)
- **UX-DR25:** Focus indicators visible (Tailwind `focus-visible:ring-2 ring-emerald-500`)
- **UX-DR26:** Stale rate banner UI when CBU.uz cache > 1 day
- **UX-DR27:** Error recovery patterns (voice fail → "yana urinish + qo'lda yoz")
- **UX-DR28:** Bottom navigation 5 tabs (Uy · + · Tarix · Qarz · Hisobot)

### FR Coverage Map

| FR Range | Epic |
|---|---|
| FR1, FR2 | Epic 0 (auth foundation) + verified by Epic 1+ |
| FR3, FR4 | Epic 10 (onboarding polish) |
| FR5-FR9 | Epic 1 (manual transaction management) |
| FR10-FR13 | Epic 1 (manual input UX) |
| FR14-FR20 | Epic 2 (voice single-tx) |
| FR21, FR23-FR25 | Epic 6 (voice multi-tx) |
| FR22 | Epic 6 (voice recurring intent) |
| FR26-FR29 | Epic 3 (categories) |
| FR30-FR38 | Epic 4 (debt tracking) |
| FR39-FR44 | Epic 5 (multi-currency) |
| FR45-FR49 | Epic 7 (recurring) |
| FR50-FR55 | Epic 8 (reports) |
| FR56-FR58 | Epic 9 (bot + notifications) |
| FR59-FR61 | Epic 1 (history) |
| FR62-FR64 | Epic 10 (settings polish; FR64 deferred) |

| NFR | Addressed in |
|---|---|
| NFR1-NFR5 (performance) | Cross-cutting; verified in Epic 10 QA |
| NFR6 (initData) | Epic 0 (middleware) |
| NFR7-NFR12 (security) | Epic 0 (HTTPS/CSP), Epic 2 (audio), Epic 1 (Decimal) |
| NFR13-NFR15 (scalability) | Epic 2 (async pipeline), Epic 5 (CBU cache) |
| NFR16-NFR18 (reliability) | Epic 0 (infra), Epic 5 (CBU fallback) |
| NFR19-NFR21 (accessibility) | Epic 10 (a11y audit) |
| NFR22-NFR24 (integration) | Epic 2 (Gemini), Epic 5 (CBU), Epic 9 (Bot) |
| NFR25-NFR30 (code quality) | Epic 0 (lint/CI setup), all epics enforce |
| NFR31-NFR34 (UX polish) | Epic 10 (polish) |

| UX-DR | Addressed in |
|---|---|
| UX-DR1, UX-DR2, UX-DR3 | Epic 0 (foundation tokens + layout) |
| UX-DR4 | Epic 1 (BalanceHero) |
| UX-DR5 | Epic 2 (VoiceButton) |
| UX-DR6 | Epic 1 (TransactionCard default) + Epic 2 (uncertain) |
| UX-DR7 | Epic 2 (single) + Epic 6 (multi-tx confirm) |
| UX-DR8 | Epic 4 (DebtRow) |
| UX-DR9 | Epic 3 (CategoryPicker) |
| UX-DR10 | Epic 1 (Numpad) |
| UX-DR11 | Epic 5 (CurrencySwitcher) |
| UX-DR12 | Epic 7 (RecurringCard) |
| UX-DR13 | Epic 8 (ReportChart) |
| UX-DR14 | Epic 8 (empty states) + Epic 10 (polish) |
| UX-DR15 | Epic 0 (Toast component) |
| UX-DR16, UX-DR17 | Epic 0 (bottom sheet + sticky CTA patterns) |
| UX-DR18 | Epic 2 (loading skeleton) + Epic 10 (polish) |
| UX-DR19 | Epic 10 (onboarding) |
| UX-DR20-UX-DR22 | Epic 0 (tokens + Inter) |
| UX-DR23 | Epic 0 (Toast + HX-Trigger pattern) |
| UX-DR24, UX-DR25 | Epic 10 (a11y) |
| UX-DR26 | Epic 5 (CBU stale banner) |
| UX-DR27 | Epic 2 (voice fail recovery) |
| UX-DR28 | Epic 0 (bottom nav layout) |

## Epic List

### Epic 0: Project Foundation
Loyihaning birinchi commit'idan deploy'gacha bo'lgan asos. Django scaffold, Telegram auth, base layout, CI/CD. Bu epikdan keyin har boshqa story shu fundament ustida quriladi.
**FRs covered:** FR1, FR2 (auth foundation) · **NFRs:** NFR6, NFR8, NFR12, NFR25-NFR30 · **UX-DRs:** UX-DR1, UX-DR2, UX-DR3, UX-DR15, UX-DR16, UX-DR17, UX-DR20-UX-DR23, UX-DR28

### Epic 1: Manual Transaction Management
Foydalanuvchi voice'siz pul yoza oladi: 4 ta tranzaksiya turi, kategoriya tanlash, summa kiritish, sof balansni Home'da ko'rish, history ko'rish va tahrirlash. Bu epik tugaganda — IWALLET allaqachon foydali tracker (voice yo'q ham).
**FRs covered:** FR5-FR13, FR59-FR61 · **UX-DRs:** UX-DR4, UX-DR6 (default), UX-DR10

### Epic 2: Voice Transaction Entry (Single)
Voice → Gemini → bitta tranzaksiya draft → confirm → save. Multi-tx EMAS — bu Epic 6'da. Bu epikdan keyin Eric birinchi marta voice bilan tranzaksiya yozadi.
**FRs covered:** FR14-FR20 · **NFRs:** NFR3, NFR9, NFR10, NFR13, NFR22 · **UX-DRs:** UX-DR5, UX-DR6 (uncertain variant), UX-DR7 (single), UX-DR18, UX-DR27

### Epic 3: Categories Management
Preset kategoriyalar mavjud + foydalanuvchi o'z kategoriyalarini emoji bilan qo'sha oladi. Bu Epic 1'dan keyin keladi — chunki Epic 1 manual flow uchun bizga preset yetadi, custom keyin.
**FRs covered:** FR26-FR29 · **UX-DRs:** UX-DR9

### Epic 4: Debt Tracking
Qarz oldim/berdim ko'rinishlari, state machine (open/partial/closed), 2 ta list, qisman qaytarish, no double-counting. Voice'da qarz tushunish ham shu yerda.
**FRs covered:** FR30-FR38 · **UX-DRs:** UX-DR8

### Epic 5: Multi-Currency Support
3 valyuta (UZS/RUB/USD), CBU.uz daily fetch, display conversion, switcher UI, stale fallback. Reports'da ham ishlatiladi.
**FRs covered:** FR39-FR44 · **NFRs:** NFR18, NFR24 · **UX-DRs:** UX-DR11, UX-DR26

### Epic 6: Voice Multi-Transaction & Recurring Intent
*"Bugun 15k taxi, 30k qahva, 200k oylik"* tipidagi multi-tx parsing + recurring intent ("har oy ijara"). Epic 2'ning kengaytmasi.
**FRs covered:** FR21, FR22, FR23, FR24, FR25 · **UX-DRs:** UX-DR7 (multi)

### Epic 7: Recurring Expenses
Takrorlanuvchi xarajatlar setup, Celery dispatch, Bot push 1-tap confirm. Bot service o'zi Epic 9'da, lekin bu epik Celery + DB tomonini quradi.
**FRs covered:** FR45-FR49, FR57 (recurring push) · **UX-DRs:** UX-DR12

### Epic 8: Reports & Analytics
Haftalik / oylik / yillik hisobotlar, SVG chartlar, valyuta switching, qarz toggle, partial-data empty state.
**FRs covered:** FR50-FR55 · **NFRs:** NFR5 · **UX-DRs:** UX-DR13, UX-DR14

### Epic 9: Telegram Bot & Notifications
Bot alohida service, webhook mode, deep-link to WebApp, qarz due push, recurring push (Epic 7 dispatch logic ishlatadi).
**FRs covered:** FR56, FR58 · **NFRs:** NFR23 · (FR57 dispatched via Epic 7 logic, sent via Bot here)

### Epic 10: Polish, Onboarding & 30-Day Readiness
Onboarding 3-card, mic permission deferred, loading/empty/error states, micro-animations, accessibility audit, settings ekran, manual QA pass. v1.0 ship gate.
**FRs covered:** FR3, FR4, FR62, FR63 · **NFRs:** NFR1, NFR19-NFR21, NFR31-NFR34 · **UX-DRs:** UX-DR14, UX-DR18, UX-DR19, UX-DR24, UX-DR25

---

## Epic 0: Project Foundation

**Goal:** Django scaffold + 10 apps + Tailwind v4 + TelegramAuthMiddleware + base layout + Caddy/systemd deploy + CI yetishtiriladi. Bu epikdan keyin har dev story to'liq, ishonchli platforma ustida quriladi.

### Story 0.1: Initialize Django Project + 10 Domain Apps

**As a** developer,
**I want** to scaffold the Django project with 10 domain-driven apps,
**So that** all subsequent stories have a consistent codebase to build on.

**Acceptance Criteria:**

**Given** an empty repository
**When** I run `django-admin startproject iwallet .` and create apps (`core`, `accounts`, `transactions`, `categories`, `debts`, `voice`, `currencies`, `recurring`, `reports`, `notifications`)
**Then** the project tree matches `docs/architecture.md` "Project Structure" exactly
**And** `pyproject.toml` includes ruff config with `target-version = "py313"` and the lint rules from `project-context.md`
**And** `requirements.txt` pins Django>=5.1,<5.2, psycopg[binary]>=3.2, django-htmx>=1.20, python-decouple>=3.8, httpx>=0.28
**And** `requirements-dev.txt` includes pytest, pytest-django, pytest-asyncio, factory-boy, djlint, pre-commit
**And** `python manage.py check` returns no errors
**And** all 10 apps appear in `INSTALLED_APPS` in `iwallet/settings/base.py`

**Given** the project is scaffolded
**When** I run `pytest`
**Then** zero tests pass (no tests yet, but pytest runs without errors)
**And** the test database is created and torn down cleanly

### Story 0.2: Single Settings File + .env Loading

**As a** developer,
**I want** one `settings.py` driven by env vars,
**So that** I don't juggle three config files for trivial differences.

**Acceptance Criteria:**

**Given** single `iwallet/settings.py` (no `settings/` package)
**When** I run `python manage.py runserver`
**Then** `DJANGO_SETTINGS_MODULE=iwallet.settings` (set in `manage.py`, `asgi.py`, `wsgi.py`)
**And** all dev/prod differences come from env vars via `python-decouple`:
  - `DEBUG = config('DEBUG', default=False, cast=bool)`
  - `ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())`
  - `DATABASE_URL = config('DATABASE_URL')`
  - `SECRET_KEY = config('SECRET_KEY')`
  - `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`, etc.

**Given** prod-only hardening (HSTS, secure cookies, structured JSON logging, strict CSP)
**When** `DEBUG = False`
**Then** these settings activate via `if not DEBUG:` blocks within the same file
**And** dev mode shows readable console logs, prod ships JSON logs

**Given** `.env.example` is committed and `.env` is gitignored
**When** I copy `.env.example` to `.env` and fill values
**Then** Django boots successfully in dev
**And** missing required env var raises clear `decouple.UndefinedValueError` on boot (no silent defaults for secrets)
**And** `.gitignore` includes `.env`, `*.pyc`, `__pycache__/`, `static/css/build.css`, `.venv/`

### Story 0.3: PostgreSQL Connection + Initial Migration

**As a** developer,
**I want** Postgres configured with persistent connections,
**So that** the app talks to a real DB from day one.

**Acceptance Criteria:**

**Given** local Postgres 16 running (Docker compose)
**When** I configure `DATABASES` in `base.py` to use `psycopg` driver with `CONN_MAX_AGE=600`
**Then** `python manage.py migrate` creates Django default tables
**And** `python manage.py dbshell` opens psql

**Given** `docker-compose.dev.yml` exists
**When** I run `docker-compose -f docker-compose.dev.yml up -d`
**Then** Postgres 16 + Redis 7 containers start with named volumes (data persists)
**And** ports 5432 and 6379 are exposed locally
**And** README documents the dev setup steps

### Story 0.4: Telegram User Model + Auth Middleware

**As a** Telegram user opening the WebApp,
**I want** to be automatically authenticated via `initData`,
**So that** I don't have to enter passwords or sign up.

**Acceptance Criteria:**

**Given** `accounts.User` model with `telegram_id` as primary key (BigInt), `first_name`, `username` nullable, `language_code` default `'uz'`, `default_currency` default `'UZS'`
**When** I run `makemigrations accounts && migrate`
**Then** `accounts_user` table exists with the columns above
**And** `User._meta.pk.name == 'telegram_id'`

**Given** `accounts.middleware.TelegramAuthMiddleware`
**When** a request hits `/app/*` with header `X-Telegram-InitData: <valid_init_data>`
**Then** middleware validates HMAC-SHA256 against `TELEGRAM_BOT_TOKEN`
**And** checks `auth_date` is within last 24 hours
**And** calls `get_or_create_user_from_init_data()` service to fetch/create the `User`
**And** attaches user to `request.user`

**Given** an invalid `initData` (bad HMAC, expired, missing)
**When** the request hits `/app/*`
**Then** middleware returns `401 Unauthorized` with body `{"error": "invalid_init_data"}`
**And** no `User` is created
**And** the failure is logged at WARNING level (no PII)

**Given** unit tests in `accounts/tests/test_middleware.py`
**When** I run `pytest accounts/`
**Then** tests cover: valid initData (pass), invalid HMAC (401), expired auth_date (401), missing header (401)
**And** coverage on `middleware.py` and `services.py` ≥80%

### Story 0.5: Base Layout + Bottom Nav + CSS Tokens

**As a** Telegram WebApp user,
**I want** a mobile-optimized layout with bottom nav,
**So that** every screen feels native and reachable.

**Acceptance Criteria:**

**Given** `core/templates/base.html`
**When** rendered
**Then** it contains `<meta viewport>` with mobile lock (`width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no`)
**And** body has `max-width: 430px; margin: 0 auto;` (mobile container even on desktop)
**And** includes htmx 2.0 and Alpine 3.14 from `static/js/`
**And** includes Telegram WebApp SDK from CDN
**And** loads compiled Tailwind CSS from `static/css/build.css`

**Given** `static/css/tokens.css`
**When** loaded
**Then** it defines CSS custom properties for: `--color-bg #FAFAF7`, `--color-surface #FFFFFF`, `--color-primary #059669`, `--color-income #10B981`, `--color-expense #0F172A`, `--color-debt #F59E0B`, plus spacing (4,8,12,16,20,24,32,48 px), and typography sizes
**And** `tailwind.config.js` imports these tokens via CSS variables

**Given** `core/templates/_nav.html` partial
**When** included in `base.html`
**Then** it renders 5 bottom nav tabs (Uy · + · Tarix · Qarz · Hisobot) with Heroicons SVG
**And** active tab is highlighted emerald-600
**And** tap targets ≥ 44×44px
**And** `safe-area-inset-bottom` padding handles iPhone notch

**Given** `core/templates/_toast.html` partial
**When** triggered via `HX-Trigger: {"toast": {"type": "success", "message": "..."}}` header
**Then** Alpine.js listens on `htmx:after-request`, displays toast top center, fades in 200ms, fades out after 3s

### Story 0.6: Tailwind CLI Build + Static Files

**As a** developer,
**I want** Tailwind compiled via CLI without webpack,
**So that** the frontend toolchain is minimal and Django collectstatic works.

**Acceptance Criteria:**

**Given** `package.json` with only `tailwindcss@^4` and `@tailwindcss/cli@^4`
**When** I run `npx tailwindcss -i static/css/app.css -o static/css/build.css --watch`
**Then** Tailwind generates purged CSS from templates and `app.css`
**And** the build is < 30 KB gzipped
**And** `build.css` is gitignored (regenerated per build)

**Given** production deploy
**When** GitHub Action runs build step
**Then** it runs `npx tailwindcss -i app.css -o build.css --minify`
**And** then `python manage.py collectstatic --noinput`
**And** Caddy serves `/static/*` directly without hitting Django

### Story 0.7: CI Pipeline (Lint + Test) on Pull Request

**As a** developer,
**I want** every PR to pass lint and tests automatically,
**So that** main branch stays green and patterns are enforced.

**Acceptance Criteria:**

**Given** `.github/workflows/ci.yml`
**When** a PR is opened
**Then** the workflow runs on Ubuntu latest, Python 3.13
**And** installs deps from `requirements.txt` + `requirements-dev.txt`
**And** runs `ruff check .`, `ruff format --check .`, `djlint --check .`
**And** spins up Postgres service, runs `pytest --cov=. --cov-report=term-missing`
**And** fails the PR if any check fails or coverage drops below 70% baseline (will rise to 80% as code grows)

**Given** `.pre-commit-config.yaml`
**When** I install hooks (`pre-commit install`)
**Then** every `git commit` runs `ruff check --fix`, `ruff format`, `djlint --reformat`, `check-added-large-files (>500KB)`, `detect-private-key`
**And** commit fails if any hook fails

### Story 0.8: Production Deploy (Caddy + uvicorn + systemd)

**As a** developer,
**I want** push-to-deploy with rollback,
**So that** I can ship safely and revert if needed.

**Acceptance Criteria:**

**Given** `deploy/systemd/iwallet-web.service` for uvicorn on port 8000
**And** `deploy/systemd/iwallet-bot.service` for uvicorn on port 8001 (used later by Epic 9)
**And** `deploy/systemd/iwallet-celery-worker.service` (used later by Epic 5/7)
**And** `deploy/systemd/iwallet-celery-beat.service` (used later by Epic 5/7)
**When** systemd starts these units (only web for now)
**Then** uvicorn loads `iwallet.asgi:application` and serves traffic
**And** `journalctl -u iwallet-web` shows JSON-formatted logs

**Given** `Caddyfile` config
**When** Caddy starts
**Then** it auto-provisions Let's Encrypt TLS for the configured domain
**And** reverse-proxies to `127.0.0.1:8000` for `/app/*`, `/static/*` from disk, `/bot/webhook/<secret>/` to `127.0.0.1:8001` (placeholder for Epic 9)
**And** sends CSP header `default-src 'self'; script-src 'self' https://telegram.org; connect-src 'self' https://api.telegram.org`

**Given** `.github/workflows/deploy.yml`
**When** I push to `main`
**Then** the workflow SSHs to the VPS, syncs code into `/srv/iwallet/releases/<sha>/`
**And** installs deps in fresh venv
**And** runs migrations
**And** flips `/srv/iwallet/current` symlink to the new release
**And** runs `systemctl restart iwallet-web`
**And** if any step fails, the symlink is NOT flipped (safe rollback)

### Story 0.9: Home Screen Placeholder + Authentication Smoke Test

**As a** Telegram user,
**I want** to open the WebApp from the bot and see a Home screen,
**So that** Epic 0 has a verifiable end-to-end success.

**Acceptance Criteria:**

**Given** `core/views.py::home_view` mapped to `/app/home/`
**When** an authenticated user (via TelegramAuthMiddleware) hits `/app/home/`
**Then** it renders `core/templates/core/home.html` extending `base.html`
**And** shows placeholder "Salom, {{ user.first_name }}!" with bottom nav
**And** the page boots in < 1.5s on simulated 3G (NFR1 baseline measurement)

**Given** a deployed dev environment + a Telegram test bot configured with the WebApp URL
**When** I open the bot in Telegram mobile and tap the WebApp button
**Then** the Home screen renders with my name and current Telegram-themed bottom nav
**And** browser console shows no errors
**And** the request is authenticated (server logs show `request.user.telegram_id`)

**Given** integration test `core/tests/test_home.py`
**When** I run pytest
**Then** test with mocked authenticated request returns 200 on `/app/home/`
**And** test with no auth header returns 401

---

## Epic 1: Manual Transaction Management

**Goal:** Foydalanuvchi 4 ta tranzaksiya turidan birini manual flow orqali yozadi, Home'da sof balansni ko'radi, History ekranida tarixini ko'radi, filterlaydi, tahrirlaydi, soft-delete'da o'chiradi va undo qiladi. Voice yo'q — kelajak epikda.

### Story 1.1: Transaction Model + Manager + Migrations

**As a** developer,
**I want** the `Transaction` model with custom manager and proper indexes,
**So that** all transaction features build on a solid data foundation.

**Acceptance Criteria:**

**Given** `transactions/models.py`
**When** the model is defined
**Then** `Transaction` has fields: `id` (BigAutoField), `user` (FK to User), `type` (CharField choices: 'income', 'expense', 'debt_lent', 'debt_borrowed'), `amount` (Decimal max_digits=15 decimal_places=2 with `CheckConstraint amount__gt=0`), `currency` (CharField 3, choices UZS/RUB/USD), `category` (FK to Category, null OK for initial deploy), `counterparty` (CharField nullable — used by debts), `date` (DateField default today), `note` (TextField nullable), `is_deleted` (Boolean default False), `deleted_at` (DateTime nullable), `created_at` and `updated_at` auto
**And** indexes: `(user, date)`, `(user, type, date)`, `(user, is_deleted)`
**And** `TransactionManager` with methods `for_user(user)` (filters user + not deleted), `in_period(start, end)`, `by_type(t)`

**Given** migration is generated and applied
**When** I open Django shell
**Then** `Transaction.objects.create(user=u, type='expense', amount=Decimal('25000'), currency='UZS', date=date.today())` succeeds
**And** trying to create with `amount=Decimal('0')` raises IntegrityError

**Given** unit tests in `transactions/tests/test_models.py`
**Then** tests cover: positive amount enforcement, manager filters, soft-delete excluded from `for_user`
**And** test coverage on the model file ≥80%

### Story 1.2: Transaction Service Layer (Create/Update/Delete/Restore)

**As a** developer,
**I want** services for transaction CRUD,
**So that** business logic lives outside views and models (SOLID).

**Acceptance Criteria:**

**Given** `transactions/services.py` with functions: `create_transaction(*, user, type, amount, currency, category, date, note=None, counterparty=None)`, `update_transaction(*, tx, **fields)`, `soft_delete_transaction(*, tx)`, `restore_transaction(*, tx)`
**When** each function is called
**Then** all writes are wrapped in `@db_transaction.atomic`
**And** `create_transaction` raises `InvalidAmountError` if amount <= 0
**And** `soft_delete_transaction` sets `is_deleted=True` and `deleted_at=now()`
**And** `restore_transaction` only works within 7 days of deletion (raises `RestoreExpiredError` after)

**Given** `transactions/exceptions.py`
**Then** it defines: `TransactionError(Exception)`, `InvalidAmountError(TransactionError)`, `RestoreExpiredError(TransactionError)`

**Given** unit tests in `transactions/tests/test_services.py`
**When** I run pytest
**Then** tests cover all 4 functions plus error cases
**And** factory-boy `TransactionFactory` is used
**And** coverage ≥80%

### Story 1.3: Category Model + Preset Seed Fixture

**As a** user,
**I want** to pick from preset categories when entering a transaction,
**So that** I don't have to create them all manually before logging anything.

**Acceptance Criteria:**

**Given** `categories/models.py::Category`
**Then** fields: `id`, `slug` (CharField unique within user+type), `name` (CharField), `emoji` (CharField 4), `type` (CharField choices income/expense), `user` (FK nullable — null = preset, FK = user custom), `is_hidden` (Boolean default False), `created_at`
**And** unique constraint on `(user, type, slug)` with `user IS NULL` allowed for presets

**Given** `categories/fixtures/preset_categories.json`
**Then** it contains 5 income presets (oylik, biznes, sovg'a, qaytgan_qarz, boshqa) and 10 expense presets (oziq_ovqat, transport, kommunal, kongilochar, kiyim, sogliq, talim, taxi, qahva_kafe, boshqa) all with emoji
**And** running `python manage.py loaddata categories/fixtures/preset_categories.json` seeds them with `user=NULL`

**Given** `categories/selectors.py::categories_for(user, type)`
**When** called
**Then** it returns user's visible categories: presets (not hidden by user) + user's custom — ordered by usage frequency desc, then alphabetical

**Given** tests in `categories/tests/`
**Then** model, fixture loading, and selector are tested with ≥80% coverage

### Story 1.4: Add Transaction Manual Form + View

**As a** user,
**I want** to enter a transaction manually with type, category, amount, and currency,
**So that** I can log money when I don't want to use voice.

**Acceptance Criteria:**

**Given** `transactions/forms.py::ManualTransactionForm` (Django Form)
**Then** fields: `type` (radio with 4 choices), `category` (Select from `categories_for(user, type)`), `amount` (Decimal field, `min_value=0.01`), `currency` (Select UZS default), `date` (Date default today), `note` (Textarea optional), `counterparty` (CharField, only required for debt types)

**Given** `transactions/views.py::add_transaction_view` (function-based, GET + POST)
**And** URL `/app/transactions/add/` named `transactions:add`
**When** GET request
**Then** renders `transactions/templates/transactions/add.html` extending `base.html` with the form
**When** POST with valid data
**Then** calls `create_transaction(...)` service, then returns `HttpResponse('', headers={'HX-Redirect': '/app/home/', 'HX-Trigger': '{"toast": {"type": "success", "message": "Tranzaksiya saqlandi"}}'})`
**When** POST with invalid data
**Then** returns 422 with form re-rendered showing inline errors (htmx swaps form back)

**Given** the form template
**Then** it includes the `Numpad` component for amount entry, with `k` and `mln` shortcuts (UX-DR10)
**And** counterparty field appears only when type is `debt_lent` or `debt_borrowed` (Alpine.js conditional render)
**And** Save button is sticky bottom with safe-area inset padding

**Given** integration tests in `transactions/tests/test_views.py`
**Then** tests cover: GET shows form, POST creates transaction, POST invalid returns errors, POST debt requires counterparty
**And** coverage ≥80%

### Story 1.5: Home Screen with BalanceHero Component

**As a** user,
**I want** Home to show my current month's balance and quick voice/manual buttons,
**So that** I see my financial state and can act in one tap.

**Acceptance Criteria:**

**Given** `core/views.py::home_view` (replacing Story 0.9 placeholder)
**When** authenticated user requests `/app/home/`
**Then** computes via `transactions/selectors.py::month_summary(user, currency=user.default_currency)`:
  - Cash balance = sum(income) − sum(expense)
  - Net balance = cash − sum(debt_borrowed not yet repaid) + sum(debt_lent not yet repaid) — for v1 simplified: cash balance only (debt logic in Epic 4)
  - This story shows ONLY cash balance + top 3 expense categories this month
**And** renders `core/templates/core/home.html`

**Given** `BalanceHero` component (`core/templates/_balance_hero.html`)
**Then** shows: currency switcher pill (top-right, just UZS for now — Epic 5 enables switching), large hero amount in Inter tabular numerals with smart formatting (UX-DR22)
**And** below: top 3 categories with emoji + amount this month
**And** loading skeleton shows while data fetches (instant for now since query is fast)

**Given** below BalanceHero
**Then** two equally-weighted buttons side-by-side: `🎤 Voice` (disabled with tooltip "Tez orada" until Epic 2) and `✏️ Qo'lda` (links to `/app/transactions/add/`)
**And** both buttons full-width-each in 50/50 split, height 56px, rounded-2xl
**And** bottom nav present (from Epic 0)

**Given** integration tests
**Then** Home view returns 200 for authenticated user
**And** displays the user's name and month summary
**And** if user has no transactions, shows empty state ("Birinchi tranzaksiyangizni qo'shing" + Qo'lda CTA)

### Story 1.6: History List + Filter + Edit + Soft-Delete

**As a** user,
**I want** to view, filter, edit, and delete my transactions,
**So that** I can fix mistakes and review what I've spent.

**Acceptance Criteria:**

**Given** `transactions/views.py::history_view` at `/app/transactions/history/`
**When** GET (no filters)
**Then** renders `transactions/history.html` showing the user's transactions in reverse chronological order (latest first), grouped by date with sticky date headers
**And** uses `select_related('category')` to avoid N+1
**And** paginates 20 per page (or infinite-scroll via htmx)

**Given** filter pills at top of history (Hammasi / Kirim / Chiqim / Qarz)
**When** user taps a pill
**Then** htmx GET `?type=expense` swaps just the list partial
**And** active pill highlighted emerald-600
**And** "Tozalash" appears when any filter active

**Given** date range filter, category filter, currency filter (in dropdown)
**When** applied
**Then** combined filters work (AND logic)
**And** URL reflects state (shareable, browser back works)

**Given** each transaction card
**When** tapped
**Then** opens `/app/transactions/<id>/edit/` modal/screen with `ManualTransactionForm` pre-filled
**When** edited form is saved
**Then** updates via `update_transaction()` service, htmx swaps card in list + toast

**Given** swipe-left on a transaction card (mobile gesture)
**When** confirmed via "O'chirish" button revealed
**Then** calls `soft_delete_transaction()`, removes card from list with 300ms animation
**And** snackbar shows "O'chirildi. Bekor qilish" with undo button (7 days valid)
**And** undo button calls `restore_transaction()`

**Given** integration tests
**Then** cover all CRUD flows with htmx headers
**And** soft-delete + restore is verified
**And** filter combinations tested
**And** coverage ≥80% on view + service

---

## Epic 2: Voice Transaction Entry (Single)

**Goal:** Mic bosib, gapirib, bitta tranzaksiyani confirm screen orqali saqlash. Async Gemini pipeline qurish, partial parse handling, error recovery.

### Story 2.1: MediaRecorder JS Module + Voice Button UX

**As a** user,
**I want** to tap the mic button and have my speech recorded clearly,
**So that** I can dictate a transaction.

**Acceptance Criteria:**

**Given** `static/js/voice-recorder.js`
**Then** it exports a class `VoiceRecorder` with methods `start()`, `stop()`, `cancel()` and events `onStateChange(state)`
**And** detects browser support for `MediaRecorder` with `audio/mp4` (iOS) or `audio/webm;codecs=opus` (Android/desktop)
**And** if no support, raises `UnsupportedError` immediately

**Given** the `VoiceButton` component (`voice/templates/voice/_voice_button.html`)
**When** rendered in Home (Epic 1 button now enabled)
**Then** 96×96 circle button with mic Heroicon
**And** states: `idle` (filled emerald), `recording` (emerald pulse animation 1.5s loop), `processing` (loading dots), `error` (red shake 300ms)
**And** state transitions are accessible (`aria-pressed`, `aria-label="Ovoz bilan tranzaksiya qo'shish"`)

**Given** user taps mic for first time
**When** browser prompts mic permission
**Then** if denied — shows error state + tooltip "Mic ruxsati kerak. Sozlamalarga o'ting yoki qo'lda yozing." with link to manual
**And** state returns to `idle`
**And** manual flow remains the default visible alternative

**Given** user taps mic with permission granted
**When** recording starts
**Then** silence detection at 1.5s of <60dB triggers auto-stop (configurable, can be disabled v1.1)
**And** maximum recording duration 60s — auto-stops with warning toast
**And** user can tap again to stop early

**Given** unit tests for the JS module are out of scope (manual smoke tests on iOS + Android)
**Then** component template renders all states (via fixture data) and verified visually

### Story 2.2: Async Voice Endpoint Scaffolding

**As a** developer,
**I want** an async Django endpoint that accepts audio,
**So that** Gemini integration can be built on top without blocking workers.

**Acceptance Criteria:**

**Given** `voice/views.py::transcribe` defined as `async def`
**And** URL `/app/voice/transcribe/` named `voice:transcribe`
**When** POST multipart with `audio` field
**Then** view reads bytes into memory (`await sync_to_async(request.FILES['audio'].read)()`)
**And** asserts size ≤ 2 MB, else returns 413 Payload Too Large
**And** asserts content-type is `audio/mp4` or `audio/webm`

**Given** `voice/services_async.py::transcribe_and_parse_async(audio_bytes, user)` — stub for now (Story 2.3 fills it in)
**When** called
**Then** returns a `list[VoiceDraft]` (empty for the stub)

**Given** the view returns `render(request, 'voice/_confirm_partial.html', {'drafts': []})` for now
**When** called from htmx (Story 2.4 finalizes the template)
**Then** htmx swaps the response into `#voice-confirm-area`

**Given** uvicorn ASGI server runs the app
**When** I send a POST with a sample webm file
**Then** the worker is non-blocking (verified by sending 5 concurrent requests, each handled in parallel within the latency budget)

**Given** integration test in `voice/tests/test_views.py` with `pytest-asyncio`
**Then** test verifies async view receives audio bytes, calls service stub, returns 200
**And** coverage on `views.py` ≥80%

### Story 2.3: Gemini Client + Parser for Single Transaction

**As a** user,
**I want** my spoken transaction parsed accurately,
**So that** I see a draft I can confirm.

**Acceptance Criteria:**

**Given** `voice/gemini_client.py::GeminiClient`
**Then** uses `httpx.AsyncClient` with timeout 30s
**And** implements `async def transcribe_and_parse(audio_bytes, user_currency_default='UZS') -> ParsedResponse` calling Gemini 2.0 Flash with structured output schema
**And** retries 3x with exponential backoff (0.5s, 1s, 2s) using a custom retry helper or `tenacity`
**And** never logs the audio bytes or the raw audio file

**Given** `voice/schemas.py`
**Then** defines dataclass `VoiceDraft` with fields per `project-context.md` (type, amount as Decimal, currency, category_slug, counterparty, date, note, confidence float, ambiguous_fields list)
**And** `ParsedResponse` containing `transactions: list[VoiceDraft]` and `recurring_intent: VoiceDraft | None`

**Given** `voice/parser.py::normalize(raw_gemini_json, user)`
**Then** converts raw Gemini response to `list[VoiceDraft]`
**And** validates and converts amounts to `Decimal` (raises with field in `ambiguous_fields` if invalid)
**And** matches `category_slug` to existing category (via `categories.selectors.match_slug(user, slug, type)`) — if no match, sets `category_slug = 'boshqa'` and adds to `ambiguous_fields`
**And** defaults date to today if missing or invalid
**And** sets `confidence` from Gemini's reported value, marks fields with confidence <0.7 as ambiguous

**Given** `voice/services_async.py::transcribe_and_parse_async(audio_bytes, user)` now wires Gemini + parser
**When** called
**Then** returns `(drafts: list[VoiceDraft], recurring: VoiceDraft | None)`

**Given** unit tests with mocked Gemini responses
**Then** tests cover: successful parse, amount as "15k" → Decimal('15000'), amount as "15 ming" → 15000, "yarim mln" → 500000, "bugun" date, ambiguous category fallback, retry on transient error, final failure after 3 retries → `GeminiUnavailableError`
**And** coverage on `gemini_client.py` and `parser.py` ≥85%

**Given** the Gemini prompt template (in `voice/prompts.py`)
**Then** instructs Gemini in Uzbek + English mix to:
  - Listen to the audio
  - Identify financial transactions
  - Return structured JSON matching our schema
  - Recognize money units: k, ming, mln, million, mlrd
  - Recognize dates: bugun, kecha, o'tgan dushanba, aniq sana
  - Recognize transaction types from context (taxi, qahva, oylik = expense/income hints; "qarz berdim/oldim" = debt)
**And** prompt template is small and reusable

### Story 2.4: Confirm Screen for Single Transaction

**As a** user,
**I want** to see my parsed transaction draft and confirm or edit it,
**So that** nothing is saved without my approval.

**Acceptance Criteria:**

**Given** `voice/templates/voice/confirm.html` extending `base.html`
**And** `voice/templates/voice/_confirm_partial.html` for htmx swap
**When** drafts list is non-empty with 1 draft
**Then** renders a single `TransactionCard` (UX-DR6) in editable variant
**And** shows fields: emoji + category (tap to change), large amount tabular-nums (tap to edit numpad), currency pill (tap to change), date pill (tap to change), counterparty if debt type, optional note
**And** all fields editable inline

**Given** the draft has any field in `ambiguous_fields` or `confidence < 0.7`
**When** rendered
**Then** card has `border-2 border-amber-500` (UX-DR uncertainty styling)
**And** uncertain field has yellow ⚠ icon and "noaniq — to'g'rilang" small text
**And** sticky bottom "Saqlash" button is **disabled** until user touches each uncertain field

**Given** the bottom of the screen
**Then** "Saqlash" primary button is sticky-bottom (Epic 0 pattern)
**And** "Bekor qilish" secondary ghost button (returns to Home)

**Given** user taps "Saqlash"
**When** the draft is valid
**Then** htmx POST to `/app/voice/save/` with the confirmed draft (JSON)
**And** server calls `transactions.services.create_transaction()`
**And** returns `HX-Redirect: /app/home/` + `HX-Trigger` for success toast

**Given** edit interactions
**When** user taps category pill
**Then** bottom sheet opens with `CategoryPicker` from Epic 3
**When** user taps amount
**Then** numpad opens (re-uses from Epic 1)
**When** user taps date
**Then** native date picker opens

**Given** integration tests
**Then** cover: draft renders correctly, ambiguous field flagged, save flows to create_transaction, edits propagate to saved record
**And** coverage ≥80%

### Story 2.5: Voice Error Handling & Recovery

**As a** user,
**I want** clear recovery paths when voice fails,
**So that** I'm never stuck.

**Acceptance Criteria:**

**Given** Gemini call fails after 3 retries with `GeminiUnavailableError`
**When** voice endpoint catches it
**Then** returns 503 with `voice/_error_partial.html` template
**And** template shows: "Gemini xizmati hozir mavjud emas. Yana urinib ko'ring yoki qo'lda yozing." + two buttons: "🎤 Qaytadan" (back to voice button) and "✏️ Qo'lda" (link to manual add)

**Given** Gemini returns no parseable transactions (empty array)
**When** voice endpoint processes
**Then** returns 422 with `_error_partial.html` showing "Tranzaksiya tushunmadim. Qaytadan urinib ko'ring."
**And** same two recovery buttons

**Given** the user's mic recorded silence (audio < 0.5s or all near-zero amplitude)
**When** client-side detects this before sending
**Then** does NOT send to server, shows toast "Hech narsa eshitilmadi" and resets to idle

**Given** integration tests
**Then** cover all three failure modes
**And** error state rendering verified
**And** manual fallback link is always present

---

## Epic 3: Categories Management

**Goal:** Foydalanuvchi preset bilan boshlasin, lekin o'z kategoriyalarini qo'sha olsin va boshqarsin.

### Story 3.1: Custom Category CRUD in Settings

**As a** user,
**I want** to add my own categories with emoji,
**So that** my spending categorization matches my life.

**Acceptance Criteria:**

**Given** `categories/views.py::category_list_view` at `/app/settings/categories/`
**When** GET
**Then** renders `categories/list.html` showing income categories and expense categories in two grouped lists
**And** each preset is shown with toggle "Yashirish/Ko'rsatish" (toggles `is_hidden` for that user)
**And** each custom category has Edit and Delete buttons

**Given** "+ Yangi kategoriya" button
**When** tapped
**Then** opens bottom sheet form with: type radio (kirim/chiqim), emoji picker (default 📌), nom (text)
**When** saved
**Then** creates a `Category(user=request.user, type=..., emoji=..., name=..., slug=slugify(name))`
**And** htmx swaps the list partial showing new category
**And** toast "Kategoriya qo'shildi"

**Given** edit/delete flows
**When** user edits a custom category
**Then** form pre-fills, save updates fields
**When** user deletes a custom category
**Then** confirmation modal ("Bu kategoriyani o'chirasizmi? Eski tranzaksiyalardan biriktirilgan bo'lsa, ular 'Boshqa' ga ko'chiriladi.")
**And** on confirm, `delete_category(...)` service migrates old transactions to "Boshqa" and deletes the category

**Given** integration tests
**Then** cover: create custom, hide preset, edit custom, delete custom with transaction migration
**And** coverage ≥80%

### Story 3.2: Category Picker Bottom Sheet Component

**As a** user,
**I want** a fast category picker grid,
**So that** I can find and pick categories quickly during transaction entry.

**Acceptance Criteria:**

**Given** `categories/templates/categories/_picker.html` partial
**When** included in any flow (Add screen, Voice confirm)
**Then** renders a grid of category chips (emoji big + label small) 4 per row on mobile
**And** "Boshqa" is always last
**And** tapping a chip selects and dismisses

**Given** the picker can open as bottom sheet (UX-DR16)
**When** triggered from a category field
**Then** slides up from bottom 300ms ease-out
**And** dismisses on tap outside, drag-down, or "Bekor qilish" button

**Given** picker shows categories sorted by usage frequency (descending) for this user, then alphabetical
**When** rendered
**Then** uses `categories.selectors.categories_for(user, type)` with frequency annotation

**Given** test in `categories/tests/test_picker.py`
**Then** template renders correctly with mocked categories
**And** sorting verified

---

## Epic 4: Debt Tracking

**Goal:** Qarz oldim/berdim, state machine, qisman qaytarish, no double-counting, 2 ta list, voice'da qarz support.

### Story 4.1: Debt Model + State Machine + DebtRepayment

**As a** developer,
**I want** a clean Debt model with explicit state machine,
**So that** edge cases (partial, closed, cancelled) are unambiguous.

**Acceptance Criteria:**

**Given** `debts/models.py`
**Then** `Debt` fields: `id`, `user` FK, `direction` (CharField choices: 'lent' = men berdim, 'borrowed' = men oldim), `counterparty` (CharField), `original_amount` (Decimal 15,2), `remaining_amount` (Decimal 15,2), `currency` (3-char), `expected_return_date` (Date nullable), `state` (CharField choices: 'open', 'partial', 'closed', 'cancelled'), `note` (Text nullable), `created_at`, `updated_at`
**And** indexes: `(user, state, direction)`

**And** `DebtRepayment` fields: `id`, `debt` FK, `amount` (Decimal 15,2), `repaid_at` (DateTime), `created_at`

**Given** `debts/state_machine.py`
**Then** defines explicit transitions:
  - `open → partial` via `apply_repayment(amount < remaining)`
  - `open → closed` via `apply_repayment(amount == remaining)`
  - `partial → partial` via additional repayment (sum < original)
  - `partial → closed` via repayment summing to original
  - `* → cancelled` via `cancel_debt(reason)` (kechirilgan or noto'g'ri kiritish)
  - Closed/cancelled debts are immutable (no further repayments)

**Given** `debts/services.py`
**Then** functions: `create_debt(...)`, `apply_repayment(debt, amount)`, `cancel_debt(debt, reason)` — all atomic
**And** `apply_repayment` enforces same currency as debt (raises `CurrencyMismatchError` if different) — v1 limitation per project-context
**And** `apply_repayment` raises `DebtAlreadyClosedError` if state is closed/cancelled
**And** all transitions logged at INFO level

**Given** `debts/exceptions.py`
**Then** defines: `DebtError`, `DebtAlreadyClosedError`, `CurrencyMismatchError`, `RepaymentExceedsRemainingError`

**Given** unit tests
**Then** cover all state transitions, edge cases (over-repayment, same-day repayment, partial then closed), coverage ≥85%

### Story 4.2: Debt Voice Support — Hook Voice Parser

**As a** user,
**I want** to dictate debt transactions,
**So that** voice flow handles all 4 transaction types.

**Acceptance Criteria:**

**Given** Gemini prompt (extends Story 2.3) recognizes patterns:
  - "Akramga 1 mln qarz berdim" → `type=debt_lent, counterparty='Akram', amount=1000000`
  - "Akramdan 500k qarz oldim" → `type=debt_borrowed, counterparty='Akram', amount=500000`
**And** parser populates `counterparty` field for debt types

**Given** voice confirm screen (Story 2.4)
**When** draft type is `debt_lent` or `debt_borrowed`
**Then** counterparty field is visible and editable in the card
**And** save creates a `Debt` (not a `Transaction`) via `debts.services.create_debt(...)`
**And** dashboard impact computed accordingly (see Story 4.4)

**Given** integration test
**Then** voice → debt draft → save → `Debt` row created in DB
**And** ambiguous counterparty (Gemini couldn't extract a name) flagged as ambiguous

### Story 4.3: Debts Screen — 2 Lists

**As a** user,
**I want** to see who owes me and who I owe,
**So that** I track interpersonal money clearly.

**Acceptance Criteria:**

**Given** `debts/views.py::debts_view` at `/app/debts/`
**When** GET
**Then** renders `debts/list.html` with two tab pills at top: "Menga qarzdor" / "Men qarzdorman"
**And** each tab shows a list of `DebtRow` components (UX-DR8) — name + initials avatar circle + amber-colored amount + state pill + "Yopish" button

**Given** the `DebtRow` component
**When** debt is `open`
**Then** shows full amount + "Yopish" action button
**When** debt is `partial`
**Then** shows remaining amount + "Qoldiq: X / Y" pill + "Yopish" button
**When** debt is `closed` or `cancelled`
**Then** does not appear in default view (separate "Tarix" tab planned for v1.1)

**Given** empty state in each tab
**When** no debts in that direction
**Then** shows `EmptyState` with "Hozircha qarz yo'q." minimal text, no CTA (debts come from voice/manual flow)

**Given** total at top of each tab
**Then** shows "Jami: X UZS" (sum of remaining amounts per currency)
**And** if multiple currencies, shows each currency on separate line

**Given** integration test
**Then** debts ekran renders for user with mock debts (open, partial, closed)
**And** "Yopish" button is present on open/partial only

### Story 4.4: Close / Partial Repay Debt Action

**As a** user,
**I want** to close or partially repay a debt with one tap,
**So that** my records stay accurate.

**Acceptance Criteria:**

**Given** user taps "Yopish" on a debt row
**When** clicked
**Then** opens bottom sheet `debts/close_form.html` with form fields: amount (default = remaining, editable via numpad), note (optional)
**And** below: text "Qoldiq: X UZS"

**Given** form is submitted via htmx POST `/app/debts/<id>/repay/`
**When** amount equals remaining
**Then** calls `debts.services.apply_repayment(debt, amount)` → state becomes `closed`
**And** htmx swaps debts list partial (row gone from open list)
**And** toast: "Qarz yopildi. Rahmat!"

**Given** amount less than remaining
**When** submitted
**Then** state becomes `partial`, `remaining_amount` decreases
**And** htmx swaps row showing new remaining + "Qoldiq" pill
**And** toast: "Qisman qaytarildi. Qoldiq: X UZS"

**Given** amount greater than remaining
**When** submitted
**Then** returns 422 with form re-rendered, inline error "Qoldiqdan ko'p miqdor kiritildi"

**Given** "Bekor qilish (kechirish)" option in close form
**When** user taps it and confirms in modal
**Then** calls `cancel_debt(debt, reason="forgiven")` → state becomes `cancelled`
**And** debt removed from active list

**Given** dashboard balance calculation (BalanceHero) now includes debts
**When** computing sof balance
**Then** sof = naqd − sum(debt_borrowed remaining) + sum(debt_lent remaining)
**And** Home BalanceHero shows 3 stats: Naqd · Sof · Qarz holati (count: M ta menga / N ta meningga qarzdorman)

**Given** integration tests
**Then** cover: full close, partial repay, over-repayment error, cancel/forgive, dashboard updates
**And** coverage ≥85%

---

## Epic 5: Multi-Currency Support

**Goal:** UZS/RUB/USD storage + CBU.uz display conversion + switcher UI + stale rate fallback.

### Story 5.1: Currency Choices Enforcement + Decimal Audit

**As a** developer,
**I want** to lock down currency codes and enforce Decimal,
**So that** money handling is safe.

**Acceptance Criteria:**

**Given** `currencies/constants.py` defining `CURRENCY_CHOICES = [('UZS', 'so\'m'), ('RUB', 'rubl'), ('USD', 'dollar')]`
**Then** all models (Transaction, Debt, ExchangeRate) reference this choices list
**And** `Decimal(15, 2)` everywhere — verified by linter rule (custom ruff check or grep for `FloatField` returns nothing)

**Given** template filter `currency_label(code)` returning "so'm/rubl/dollar"
**Then** used everywhere instead of raw 'UZS' string in UI

**Given** linting / CI step
**When** any new code introduces `FloatField` or `float()` on money fields
**Then** PR is blocked

### Story 5.2: ExchangeRate Model + CBU.uz Client

**As a** developer,
**I want** to fetch daily rates and store them,
**So that** display conversion is deterministic.

**Acceptance Criteria:**

**Given** `currencies/models.py::ExchangeRate`
**Then** fields: `currency` (3-char), `rate_to_uzs` (Decimal 15,6 — higher precision for rate), `date` (Date), `fetched_at` (DateTime)
**And** unique constraint `(currency, date)`

**Given** `currencies/cbu_client.py::fetch_cbu_rates()`
**Then** uses `httpx.Client` (sync OK for cron task), calls `https://cbu.uz/uz/arkhiv-kursov-valyut/json/`
**And** filters response to USD and RUB
**And** retries 5x with backoff, raises `CbuUnavailableError` after final fail
**And** returns dict like `{'USD': Decimal('12345.67'), 'RUB': Decimal('134.56'), 'date': date(2026, 6, 25)}`

**Given** `currencies/services.py::store_rates(date, rates)`
**Then** upserts `ExchangeRate` for each currency for that date
**And** is atomic per call

**Given** unit tests with mocked CBU response
**Then** parsing works, retry logic verified, stale fallback returns last `ExchangeRate` if today's not available
**And** coverage ≥85%

### Story 5.3: Celery Beat — Daily CBU Fetch + Boot Reactor

**As a** developer,
**I want** rates refreshed automatically every day,
**So that** display conversion is current without manual intervention.

**Acceptance Criteria:**

**Given** Celery app configured (`iwallet/celery.py`) with Redis broker
**And** `currencies/tasks.py::refresh_cbu_rates()` Celery task
**When** called
**Then** invokes `fetch_cbu_rates()` then `store_rates()`
**And** on failure, logs warning and exits (does NOT raise — stale fallback covers)

**Given** Celery Beat schedule (in `iwallet/celery.py`)
**Then** runs `refresh_cbu_rates` daily at 09:00 Asia/Tashkent
**And** systemd unit `iwallet-celery-beat.service` enabled

**Given** boot-time behavior
**When** the app starts
**Then** management command `python manage.py refresh_rates` exists for manual one-off (e.g., on first deploy before Beat ticks)

**Given** integration test (with mocked CBU)
**Then** task creates ExchangeRate records correctly
**And** failure doesn't crash worker

### Story 5.4: Display Conversion Helper + Stale Fallback

**As a** developer,
**I want** a single `convert_for_display(amount, from_currency, to_currency)` helper,
**So that** all balance/report calculations use one path.

**Acceptance Criteria:**

**Given** `currencies/services.py::convert_for_display(amount, from_currency, to_currency, as_of_date=None)`
**Then** when `from == to`, returns amount unchanged
**When** `from == 'UZS'` and `to == 'USD'`, divides by today's USD rate
**When** `from == 'USD'` and `to == 'UZS'`, multiplies by USD rate
**When** USD ↔ RUB, converts via UZS intermediary (USD→UZS→RUB)
**And** uses `as_of_date or today()` to look up rate; if missing, uses most recent `ExchangeRate` and returns tuple `(converted_amount, rate_is_stale: bool, rate_date: date)`

**Given** `currencies/selectors.py::current_rates_stale_days()`
**Then** returns int of days since the latest rate fetch
**When** > 1 day
**Then** views set context `rates_stale_days` so templates can display banner

**Given** unit tests
**Then** cover: same currency, UZS↔USD, USD↔RUB cross-conversion, stale fallback, missing rate edge case
**And** coverage ≥85%

### Story 5.5: Currency Switcher UI + Stale Banner

**As a** user,
**I want** to switch the display currency on Home and Reports,
**So that** I view my balance in my preferred currency.

**Acceptance Criteria:**

**Given** `CurrencySwitcher` component (`currencies/templates/currencies/_switcher.html`)
**When** rendered in Home BalanceHero
**Then** shows pill button labeled with current display currency (e.g., "UZS")
**When** tapped
**Then** opens bottom sheet listing UZS/RUB/USD options
**When** option selected
**Then** htmx GET `/app/home/?display_currency=USD` swaps the balance hero partial with converted amounts
**And** preference persisted to user's `display_currency_preference` (session-level v1 — full persistence v1.1)

**Given** display currency is anything other than UZS
**When** BalanceHero renders
**Then** also shows small text "≈ USD bo'yicha" beneath amount (so user remembers it's display only)

**Given** `rates_stale_days > 1`
**When** any page with conversion renders
**Then** top banner shows "💱 Valyuta kursi {N} kun eski. Tranzaksiyalar normal saqlanmoqda."
**And** banner is dismissible (Alpine.js state, until next stale event)
**And** banner does NOT block UX (NFR18, UX-DR26)

**Given** integration tests
**Then** cover switching display, persistence within session, stale banner appearance/dismiss
**And** coverage ≥80%

---

## Epic 6: Voice Multi-Transaction & Recurring Intent

**Goal:** Bir gapda 2-5 ta tranzaksiya parse qilish + recurring intent ("har oy ijara") → recurring sozlamaga taklif.

### Story 6.1: Multi-Transaction Parser

**As a** user,
**I want** to dictate multiple transactions in one phrase,
**So that** I can log a day's spending at once.

**Acceptance Criteria:**

**Given** Gemini prompt is updated (extends Story 2.3) to handle multi-transaction utterances
**Then** the prompt explicitly instructs Gemini that one audio may contain 1-N transactions
**And** schema returned is always `transactions: list[VoiceDraft]` (1+ items)

**Given** sample test phrases (manually generated test fixtures):
  - *"Bugun 15k taxi, 30k qahva ichdim, 200k oylik tushdi"* → 3 drafts
  - *"Akramga 1 mln qarz berdim va do'kondan 50k oziq-ovqat"* → 2 drafts
  - *"15 ming taxida yurdim"* → 1 draft
**When** sent to the parser
**Then** correct number of drafts returned with correct types/amounts
**And** the parser unit test uses recorded Gemini response fixtures (not live API in tests)

**Given** when one transaction in a batch is ambiguous (confidence < 0.7)
**When** parsed
**Then** that draft is flagged but others remain clear
**And** the full list is still returned

**Given** unit tests in `voice/tests/test_parser.py` with Gemini response fixtures
**Then** cover multi-tx parsing, mixed clear/ambiguous drafts, edge case "k", "ming", "mln" mixed in one phrase
**And** coverage ≥85%

### Story 6.2: Confirm Screen for Multiple Drafts

**As a** user,
**I want** to see, edit, and approve multiple drafts at once,
**So that** I don't have to repeat the voice flow per transaction.

**Acceptance Criteria:**

**Given** the confirm screen template (extends Story 2.4)
**When** `len(drafts) > 1`
**Then** renders N stacked `TransactionCard`s vertically, each editable independently
**And** top header shows "N ta tranzaksiya" + total summary "−A UZS · +B UZS · qarz C UZS"
**And** each card has its own edit/delete (swipe) actions

**Given** any card has uncertain fields
**When** rendered
**Then** sticky bottom "Saqlash" button is **disabled** until all uncertain fields are touched/resolved
**And** unresolved count shown: "1 ta kartada noaniq maydon bor"

**Given** user deletes a draft (swipe left → confirm)
**When** confirmed
**Then** card removed via htmx swap, counter updates, sticky button updates

**Given** user taps "Saqlash"
**When** all drafts valid
**Then** htmx POST `/app/voice/save-multi/` with all confirmed drafts as JSON
**And** server calls `transactions.services.create_transaction()` for each in a single `db_transaction.atomic` block — all-or-nothing per FR25
**And** if any single insert fails (rare — DB issue), entire batch rolls back, error toast
**And** success: htmx HX-Redirect to `/app/home/` + toast "N ta tranzaksiya saqlandi"

**Given** integration tests
**Then** cover multi-draft render, per-card edit, batch save atomicity, single failure rollback, debt + transaction mixed batch
**And** coverage ≥85%

### Story 6.3: Voice Recurring Intent Detection

**As a** user,
**I want** my "har oy ijara" phrase to offer creating a recurring entry,
**So that** I don't have to set it up manually.

**Acceptance Criteria:**

**Given** Gemini prompt is extended to detect phrases like "har oy", "har hafta", "har dushanba", "oylik", "haftalik"
**And** when detected, response field `recurring_intent` is populated with `VoiceDraft` plus a `schedule_hint` ("monthly" / "weekly" / "monthly:day=1" etc.)

**Given** parser returns `(drafts, recurring_intent)`
**When** `recurring_intent is not None`
**Then** confirm screen shows it as a special card with header "Takrorlanuvchi? 🔄"
**And** offers two actions: "Recurring qilib qo'shish" (creates RecurringSchedule entry from Epic 7) and "Faqat bu safargi tranzaksiya" (treats as single)

**Given** if Epic 7 (RecurringSchedule model) is not yet implemented at the time this story is done in sequence
**Then** this story's recurring action button shows tooltip "Tez orada" and is disabled
**And** the recurring intent detection still works in the parser (data collected, just no model write)
**And** later Epic 7 Story enables the action

**Given** integration tests
**Then** cover: detection in parser, special card render, action buttons present
**And** coverage ≥80%

---

## Epic 7: Recurring Expenses

**Goal:** RecurringSchedule CRUD + Celery dispatch + Settings UI. Bot push is Epic 9.

### Story 7.1: RecurringSchedule Model + CRUD Service

**As a** developer,
**I want** RecurringSchedule model and services,
**So that** recurring entries can be created, listed, edited, deleted.

**Acceptance Criteria:**

**Given** `recurring/models.py::RecurringSchedule`
**Then** fields: `id`, `user` FK, `type` (income/expense/debt_*), `name` (e.g., "Ijara"), `amount` Decimal(15,2), `currency` (3-char), `category` FK to Category, `schedule_kind` (CharField: 'monthly' / 'weekly'), `day_of_month` (Int 1-31 nullable), `day_of_week` (Int 0-6 nullable), `next_dispatch_at` (Date), `is_active` (Boolean default True), `created_at`, `updated_at`

**Given** `recurring/services.py`
**Then** functions: `create_recurring(...)`, `update_recurring(...)`, `delete_recurring(...)`, `compute_next_dispatch_date(schedule)`, `mark_dispatched(schedule)` (advances `next_dispatch_at`)
**And** `compute_next_dispatch_date` handles month-end edge cases (Feb 30 → Feb 28, etc.) per project-context rule

**Given** unit tests
**Then** cover all CRUD, next-date computation including leap year February, weekly cycling
**And** coverage ≥85%

### Story 7.2: Settings — Recurring CRUD UI

**As a** user,
**I want** to view and manage my recurring entries in Settings,
**So that** I see what's set up and can edit/disable.

**Acceptance Criteria:**

**Given** `recurring/views.py::recurring_list_view` at `/app/settings/recurring/`
**When** GET
**Then** renders list of user's `RecurringSchedule`s using `RecurringCard` (UX-DR12)
**And** each card shows: schedule (har dushanba / har 1-chi / etc.) + nom + amount + currency + active toggle + edit/delete

**Given** "+ Yangi" button
**When** tapped
**Then** opens form bottom sheet with: type, name, amount (numpad), currency, category picker, schedule_kind selector, day picker (1-31 for monthly, weekday for weekly)
**When** saved
**Then** creates via service, htmx swaps list

**Given** edit/delete flow
**When** edited or deleted
**Then** service called, list updated
**And** delete shows confirmation

**Given** voice recurring intent action (from Epic 6 Story 6.3) now wired
**When** user taps "Recurring qilib qo'shish" on a voice draft
**Then** redirects to recurring create form pre-filled

**Given** integration tests
**Then** cover CRUD + voice-to-recurring deep-link
**And** coverage ≥80%

### Story 7.3: Celery Beat — Daily Recurring Dispatch

**As a** developer,
**I want** Celery to dispatch reminders for due schedules,
**So that** users get bot push (sent in Epic 9).

**Acceptance Criteria:**

**Given** `recurring/tasks.py::dispatch_due_recurring_reminders()` Celery task
**When** runs (scheduled daily via Beat at 09:00 Tashkent)
**Then** finds all `RecurringSchedule(is_active=True, next_dispatch_at__lte=today)`
**And** for each, creates a `notifications.PushQueueItem` row (defined in Epic 9 — for now Stub model with minimal fields: `user`, `payload_json`, `kind`, `created_at`)
**And** calls `mark_dispatched(schedule)` advancing `next_dispatch_at`

**Given** Celery Beat schedule
**When** running
**Then** scheduled task `dispatch_due_recurring_reminders` registered with cron 09:00 Asia/Tashkent

**Given** integration test with frozen time
**Then** verifies: schedule due today → push queued, next_dispatch_at advanced
**And** schedule not due → nothing happens
**And** disabled schedule → skipped

---

## Epic 8: Reports & Analytics

**Goal:** Haftalik, oylik, yillik report bilan kategoriya pie + kunlik bar + trend bar + top 5 + valyuta toggle + qarz toggle + partial-data empty states.

### Story 8.1: Report Selectors (Aggregations)

**As a** developer,
**I want** efficient selectors for weekly/monthly/yearly aggregations,
**So that** reports render fast (NFR5).

**Acceptance Criteria:**

**Given** `reports/selectors.py`
**Then** functions:
  - `weekly_summary(user, start_date, currency)` returns `{by_category: dict, by_day: list, total_income, total_expense}` (UZS converted display)
  - `monthly_summary(user, year, month, currency)` returns same shape + `top_5_expenses` (list of (category, amount))
  - `yearly_summary(user, year, currency)` returns `{by_month: list of 12, top_categories: list, most_expensive_month: dict}`
  - All use `select_related` and `annotate` for single-query efficiency
  - All accept `include_debts: bool` parameter

**Given** unit tests with seeded factory data (multiple users, 3 currencies, mixed types)
**Then** verify aggregations correct including edge cases (empty period, single transaction, multi-currency present)
**And** N+1 not triggered (verify via `assertNumQueries` ≤ 5 per call)
**And** coverage ≥85%

### Story 8.2: Weekly Report View + SVG Pie + Bar Charts

**As a** user,
**I want** a weekly breakdown by category and day,
**So that** I see where my recent money went.

**Acceptance Criteria:**

**Given** `reports/views.py::weekly_view` at `/app/reports/weekly/`
**When** GET (default = current week, Monday-Sunday)
**Then** renders `reports/weekly.html` with current week summary
**And** week navigation arrows (← previous / next →) cycle weeks

**Given** `reports/charts.py::svg_pie(data, colors)` and `svg_bar(data, color)`
**When** called with category data
**Then** returns inline SVG markup with title + desc for a11y, fixed viewport sized for mobile (300×300)
**And** each slice clickable filtering history to that category (`<a href="/app/transactions/history/?category=X">`)

**Given** the page shows:
  - Top: total income (emerald) + total expense (slate) + delta
  - Pie: expense distribution by category (top 6 categories + "Boshqalar")
  - Bar: daily spending Mon-Sun
  - Toggle: "Qarzlarni ko'rsatish" (sets `include_debts=true`)
  - Currency switcher (Epic 5)
**And** if no data this week: `EmptyState` "Bu hafta tranzaksiya yo'q"

**Given** integration tests
**Then** verify view renders, SVG markup correct, currency conversion applied, empty state shown
**And** coverage ≥80%

### Story 8.3: Monthly Report View

**As a** user,
**I want** a monthly view with trend and top 5,
**So that** I review the month at a glance.

**Acceptance Criteria:**

**Given** `reports/views.py::monthly_view` at `/app/reports/monthly/`
**When** GET (default = current month)
**Then** renders monthly summary using `monthly_summary` selector
**And** month nav arrows cycle months

**Given** the page shows:
  - Income vs expense trend (small bar pair)
  - Top 5 expenses with category emoji + amount
  - Valyuta bo'yicha taqsimot (if multi-currency present)
  - Pie of category distribution
  - Same toggles as weekly (qarz, currency)
**And** if month is empty: empty state

**Given** integration tests
**Then** cover rendering, multi-currency split present, navigation
**And** coverage ≥80%

### Story 8.4: Yearly Report View + Partial Data Handling

**As a** user,
**I want** yearly trends shown,
**So that** I see annual patterns even with partial data.

**Acceptance Criteria:**

**Given** `reports/views.py::yearly_view` at `/app/reports/yearly/`
**When** GET (default = current year)
**Then** renders `reports/yearly.html`

**Given** user has < 3 months of data in selected year
**When** rendered
**Then** shows `EmptyState` "Ma'lumot to'planmoqda. Yillik hisobot kamida 3 oydan keyin ma'lumotli bo'ladi."
**And** still shows available month bars (partial data, with months without data as empty gray bars)

**Given** user has ≥ 3 months of data
**When** rendered
**Then** shows:
  - 12-month bar chart (income+expense per month)
  - Highlighted most expensive month
  - Top categories (all year)
  - Year-over-year comparison if previous year has data; otherwise omit

**Given** integration tests with seeded data covering 0/2/6/12 months
**Then** verify each branch
**And** coverage ≥80%

---

## Epic 9: Telegram Bot & Notifications

**Goal:** Bot alohida service (port 8001), webhook mode, deep-link to WebApp, qarz due push, recurring push dispatch.

### Story 9.1: Bot Service Skeleton + Webhook Endpoint

**As a** developer,
**I want** the Telegram Bot running as a separate uvicorn service,
**So that** it doesn't affect WebApp performance.

**Acceptance Criteria:**

**Given** `notifications/bot/main.py` runs `python-telegram-bot` v21 in webhook mode
**And** `notifications/bot/webhook.py` exposes ASGI app handling `POST /bot/webhook/<secret>/` where `<secret>` matches `TELEGRAM_WEBHOOK_SECRET` env var
**When** uvicorn runs this on port 8001
**Then** Caddy reverse-proxies `/bot/webhook/<secret>/` to localhost:8001
**And** systemd unit `iwallet-bot.service` enabled (from Epic 0)

**Given** `/start` command handler in `notifications/bot/handlers.py`
**When** user sends `/start` (with or without deep-link payload)
**Then** bot replies with "Salom! IWALLET'ga xush kelibsiz. Mahnamod boshlash uchun pastdagi tugmani bosing." + WebApp inline keyboard button

**Given** deep-link payload (e.g., `/start action_recurring__42`)
**When** received
**Then** bot reply includes WebApp button with URL containing the action: `t.me/iwallet_bot/app?startapp=action_recurring__42`

**Given** integration tests using Telegram Bot test framework or HTTP mocking
**Then** webhook receives messages, dispatches to handlers, /start works
**And** coverage on handlers ≥80%

### Story 9.2: Notification Service + PushQueueItem Model

**As a** developer,
**I want** a queue of pending notifications,
**So that** dispatch is decoupled from Telegram send (retry-able).

**Acceptance Criteria:**

**Given** `notifications/models.py::PushQueueItem`
**Then** fields: `id`, `user` FK, `kind` (CharField: 'recurring' / 'debt_due'), `payload_json` (JSONField — contains `action_link`, `text`, related entity id), `status` ('pending' / 'sent' / 'failed'), `attempts` (Int), `created_at`, `sent_at` (DateTime nullable)

**Given** `notifications/services.py::send_push(item)` (Celery task)
**Then** uses Telegram Bot API to send message to user's `telegram_id`
**And** retries 3x on transient errors (network, 429, 5xx)
**And** marks item `sent` or `failed` accordingly
**And** never blocks WebApp threads (Celery worker)

**Given** Celery task `notifications.tasks.dispatch_pending_pushes` runs every 60s
**When** runs
**Then** finds `PushQueueItem(status='pending')`, picks up to 100, calls `send_push` for each

**Given** integration tests with mocked Telegram API
**Then** cover successful send, retry on transient error, final failure
**And** coverage ≥80%

### Story 9.3: Debt Due Reminders (Daily Scheduler)

**As a** user,
**I want** to be reminded 1 day before a debt repayment is due,
**So that** I close debts on time.

**Acceptance Criteria:**

**Given** `notifications/tasks.py::queue_debt_due_reminders()` Celery Beat task (daily 08:00 Tashkent)
**When** runs
**Then** finds `Debt(state__in=['open','partial'], expected_return_date=tomorrow)`
**And** queues a `PushQueueItem(kind='debt_due')` for each with payload `{action_link: 't.me/iwallet_bot/app?startapp=action_debt_close__<id>', text: 'Akram qarzni qaytarish kuni: ertaga (500k UZS).'}`

**Given** the user receives push
**When** taps the inline button
**Then** Telegram opens WebApp with `action_debt_close__<id>` payload
**And** WebApp (via Story 9.5) handles the action by opening the debt close form pre-filled

### Story 9.4: Recurring Push Send + 1-Tap Confirm

**As a** user,
**I want** my recurring expense reminder with a 1-tap confirm,
**So that** I add it without typing.

**Acceptance Criteria:**

**Given** Epic 7 Story 7.3 enqueues `PushQueueItem(kind='recurring')` daily
**When** the dispatcher picks one up
**Then** message text: "Bugun {schedule.name} kuni. {amount} {currency} qo'shaylikmi?"
**And** inline keyboard: "✓ Ha (qo'shish)" + "✗ Yo'q" + "Tahrir qilish"
**And** "Ha" callback queries the bot's `confirm_recurring(schedule_id)` handler which calls `transactions.services.create_transaction(...)` directly (no WebApp open needed)
**And** "Yo'q" callback removes the queue item, bot replies "Tushunarli, ertaga eslataman emas."
**And** "Tahrir" callback opens WebApp with `action_recurring__<id>` for full edit

**Given** integration tests with bot handlers
**Then** cover all 3 callback paths
**And** coverage ≥80%

### Story 9.5: Deep-Link Action Handler in WebApp

**As a** user,
**I want** the WebApp to open the right pre-filled screen when I tap a bot link,
**So that** flow is seamless.

**Acceptance Criteria:**

**Given** WebApp boot in `base.html` JS reads `window.Telegram.WebApp.initDataUnsafe.start_param`
**When** matches pattern `action_<type>__<id>`
**Then** JS makes htmx request to `/app/actions/<type>/<id>/`
**And** server view dispatches to the right pre-filled screen:
  - `action_recurring__<id>` → recurring edit form
  - `action_debt_close__<id>` → debt close form pre-filled with that debt

**Given** `core/views.py::action_dispatch_view`
**When** receives valid action
**Then** redirects (htmx) to the right pre-filled URL
**When** action_id doesn't exist or doesn't belong to user
**Then** falls back to Home with toast "Eski havola"

**Given** integration tests
**Then** cover all action types + invalid action
**And** coverage ≥80%

---

## Epic 10: Polish, Onboarding & 30-Day Readiness

**Goal:** Onboarding, all loading/empty/error states, micro-animations, accessibility audit, Settings ekran, final QA.

### Story 10.1: Onboarding Flow (3 Cards + Deferred Mic Permission)

**As a** first-time user,
**I want** a quick orientation,
**So that** I know what IWALLET is and how to start.

**Acceptance Criteria:**

**Given** `accounts/views.py::onboarding_view` at `/app/onboarding/`
**When** user lands and `user.created_at` was within last 5 minutes AND user has zero transactions
**Then** middleware redirects to onboarding on Home access
**When** user lands at onboarding
**Then** shows 3 cards in swipeable carousel:
  - Card 1: "IWALLET — Telegram'da pulingni 10 soniyada yozasan" + minimal illustration text
  - Card 2: 4 transaction types visual ("Kirim · Chiqim · Qarz oldim · Qarz berdim") + emoji
  - Card 3: "Voice yoki qo'lda — har ikkisi ham ishlaydi. Voice uchun mic ruxsati keyinroq so'raladi."

**Given** "Boshlash" button on last card
**When** tapped
**Then** marks user as onboarded (`User.onboarded_at = now()` — add field via migration)
**And** redirects to Home

**Given** the user can skip via "O'tkazib yuborish"
**When** tapped
**Then** marks onboarded immediately, redirects to Home

**Given** mic permission is NOT requested during onboarding
**When** user first taps the voice button on Home post-onboarding
**Then** small toast/banner explains "Ovoz uchun mic ruxsati kerak. Audio biz tomondan saqlanmaydi." before browser prompt
**And** this contextual prompt verified by integration test

**Given** integration tests
**Then** cover: first-time redirect, swipe through cards, skip, mark onboarded, voice contextual permission
**And** coverage ≥80%

### Story 10.2: Loading Skeletons + Optimistic UI Audit

**As a** user,
**I want** every loading state to feel fast,
**So that** I never see blank screens or spinners.

**Acceptance Criteria:**

**Given** every htmx swap that takes > 100ms
**Then** has `hx-indicator` showing a skeleton matching the eventual content shape (gray gradient placeholder)
**And** no GIF or SVG spinner anywhere

**Given** save actions (manual add, debt close, voice save)
**When** user taps save
**Then** the destination screen (Home, debts list) updates optimistically (assume success) immediately
**And** htmx swap happens in background; on failure, error toast and revert

**Given** all screens are audited via manual checklist:
  - Home: skeleton during initial load, balance tween animation 300ms on update
  - Add: numpad responsive (no input lag)
  - History: skeleton list during scroll/filter
  - Debts: skeleton row during close action
  - Reports: skeleton chart during data fetch
  - Voice: skeleton cards during Gemini processing
**Then** all verified in dev tools throttle 3G mode

### Story 10.3: Empty States + Error Recovery Across All Screens

**As a** user,
**I want** every empty or error screen to tell me what to do,
**So that** I'm never stuck.

**Acceptance Criteria:**

**Given** the following empty states are implemented with `EmptyState` component:
  - Home: no transactions → "Birinchi tranzaksiyangizni qo'shing" + Voice/Manual CTA
  - History: filter returns 0 → "Filterga mos tranzaksiya yo'q. [Tozalash]"
  - Debts: no open debts → "Qarz yo'q. Sof balans aniq."
  - Reports yearly < 3 months: "Ma'lumot to'planmoqda. Hafta-2 dan keyin qayting."
  - Reports weekly/monthly with no data: "Bu davrda tranzaksiya yo'q."
  - Settings recurring empty: "Takrorlanuvchi xarajatingiz yo'q. [Qo'shish]"

**Given** the following error states implemented:
  - Voice fail: handled in Epic 2 Story 2.5
  - Network error on save: "Internet bog'lanmagan. [Qaytadan urinish]"
  - CBU stale: handled in Epic 5 Story 5.5
  - Generic 500: "Texnik nosozlik. Ishlab chiquvchilarga xabar yuborildi. Qaytadan urinib ko'ring."

**Given** manual QA checklist passes for all 12+ empty/error states
**Then** each state visually verified in dev tools

### Story 10.4: Micro-Animations & Polish

**As a** user,
**I want** subtle motion that confirms my actions,
**So that** the app feels alive and responsive.

**Acceptance Criteria:**

**Given** the following animations implemented (all 200-300ms ease-out unless noted):
  - BalanceHero amount tween on update (count up from old to new)
  - Save button: press → shrink 0.95 then back (haptic-like)
  - Toast: slide in from top, slide out
  - Bottom sheet: slide up from bottom
  - Card swipe-to-delete: card slides off, list reflows
  - Voice mic: pulse animation during recording (1.5s loop)
  - htmx swap fade-in 150ms

**Given** `@media (prefers-reduced-motion: reduce)` rule
**Then** disables all non-essential transitions, keeps only opacity changes

**Given** lint checks for animation budgets
**Then** no animation > 400ms in app.css

**Given** manual QA passes on iOS + Android Telegram WebApp
**Then** animations feel smooth (60fps), no jank

### Story 10.5: Accessibility Audit (WCAG 2.1 AA)

**As a** user with disabilities,
**I want** the app to work with assistive technologies,
**So that** I can manage money independently.

**Acceptance Criteria:**

**Given** automated audit via Lighthouse
**Then** accessibility score ≥ 90
**And** axe-core via DevTools shows 0 critical or serious issues

**Given** manual accessibility checklist:
  - All interactive elements have visible focus indicators
  - All icon-only buttons have `aria-label` in Uzbek
  - Color contrast verified ≥ 4.5:1 on text (token palette already designed for this)
  - Touch targets ≥ 44×44px verified on every screen
  - Forms have associated `<label>` elements
  - Errors announced via `role="alert"` and `aria-live="polite"`
  - Heading hierarchy correct on every page (h1 once, no skipping)
  - `<html lang="uz">` set
**Then** all items verified

**Given** screen reader testing
**Then** iOS VoiceOver: complete voice transaction flow announced correctly
**And** Android TalkBack: same flow works

**Given** keyboard-only testing
**Then** tab through all interactive elements on every screen
**And** every action accessible without touch (where applicable)

### Story 10.6: Settings Screen (Full)

**As a** user,
**I want** Settings to manage my preferences,
**So that** I control my IWALLET experience.

**Acceptance Criteria:**

**Given** `core/views.py::settings_view` at `/app/settings/`
**When** GET
**Then** renders `settings.html` showing groups:
  - Profile: name (from Telegram, read-only), language (uz only v1)
  - Valyuta: default valyuta (Select UZS/RUB/USD) + display valyuta preference
  - Kategoriyalar: link to Epic 3 categories settings
  - Recurring xarajatlar: link to Epic 7 recurring settings
  - Privacy: text "Audio fayllar saqlanmaydi. Gemini'ga matnga aylantirish uchun yuboriladi. Free tier: Google ovozni training uchun ishlatishi mumkin." (FR63)
  - About: app version, links to terms/privacy (placeholder for v2 omma chiqishi)
  - Account: "Hisobni tozalash" button (deletes user + all data — confirm modal with strong wording)

**Given** "Default valyuta" change
**When** user selects new currency
**Then** `User.default_currency` updated, Home reflects on next visit

**Given** "Hisobni tozalash"
**When** user confirms via modal "BARCHA MA'LUMOTLARNI O'CHIRAMAN" typed
**Then** soft-deletes all user data (cascade) — actual hard delete v1.1 to allow recovery in case
**And** redirects to onboarding

**Given** integration tests
**Then** cover settings view, default currency update, profile read-only verify
**And** coverage ≥80%

### Story 10.7: 30-Day Self-Trial Manual QA Pass

**As a** product owner,
**I want** to manually verify the entire app works end-to-end,
**So that** v1.0 is ready for my 30-day solo trial.

**Acceptance Criteria:**

**Given** a comprehensive manual QA checklist:
  - [ ] Open WebApp from Telegram bot on iOS — Home renders < 2s on 3G
  - [ ] Open WebApp from Telegram bot on Android — Home renders < 2s on 3G
  - [ ] Voice single tx: 10 phrases each in UZS context, ≥85% parsed correctly
  - [ ] Voice multi tx: 5 multi-phrases, all drafts editable
  - [ ] Voice recurring: 3 phrases detected
  - [ ] Manual flow: all 4 transaction types, all 3 currencies
  - [ ] Debt: create, partial repay, full close, cancel — all work correctly
  - [ ] CBU.uz: turn off internet on server briefly, verify stale banner appears, transactions still save
  - [ ] Reports: weekly/monthly with sample data, yearly with < 3 months shows empty state
  - [ ] Bot push: recurring + debt due both fire, 1-tap confirm works
  - [ ] Onboarding: fresh user goes through cards
  - [ ] Settings: all options work
  - [ ] Edge cases: zero amount blocked, future date clamped, over-repay error
  - [ ] Network throttle 3G: all flows usable, no timeouts < 30s
  - [ ] iOS VoiceOver + Android TalkBack: voice flow announced correctly
**When** Eric runs this checklist on a deployed dev environment
**Then** all items pass or have documented exceptions
**And** any failures filed as bugs and resolved before v1.0 deploy

**Given** the 30-day trial commences post-checklist
**When** Eric uses the app daily
**Then** he tracks: voice STT accuracy (note any misparses), latency feel, any UI friction, any crashes/errors
**And** at day 30, evaluates against PRD success criteria (>80% transactions in app, <10s voice avg, ±5% balance accuracy)
**And** if metrics met → proceed to closed beta (Mary's continuous discovery plan); if not → iterate

---

**Total: 11 epics, 56 stories.** All FRs (FR1-FR64) covered. All UX-DRs (UX-DR1-UX-DR28) covered. All NFRs traced to verification stories.

Each story is independently completable using only earlier stories' output (no forward dependencies). Each epic delivers user value standalone (Epic 1 ships as a usable manual tracker even without voice; Epic 4 adds debt without requiring reports; etc.).

Ready for development. Sprint 0 starts with Story 0.1 (project scaffold).
