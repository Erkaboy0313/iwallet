---
project_name: 'IWALLET'
user_name: 'Eric'
date: '2026-06-25'
sections_completed:
  - technology_stack
  - language_rules
  - framework_rules
  - testing_rules
  - code_quality_rules
  - workflow_rules
  - critical_dont_miss_rules
existing_patterns_found: 47
---

# Project Context for AI Agents — IWALLET

> Loyihada kod yozayotgan har bir AI agent (Amelia, future devs, Claude Code, Copilot...) ushbu qoidalarni **majburiy** o'qishi kerak. Bu hujjat *aniq* qoidalarni saqlaydi — *nima uchun*'larni emas (ular `architecture.md`'da). Maqsad: agent xato qilmasligi va konsistentlik.

---

## Technology Stack & Versions

| Layer | Texnologiya | Versiya | Eslatma |
|---|---|---|---|
| Runtime | Python | 3.13+ | async views uchun |
| Backend framework | Django | 5.1 LTS | async ORM cheklangan — `sync_to_async` ishlatiladi voice ORM uchun |
| ASGI server | uvicorn | latest stable | gunicorn YOQ — async views talab qiladi ASGI |
| Database | PostgreSQL | 16+ | JSONB + Decimal |
| Cache / Queue broker | Redis | 7.x | Celery broker + future cache |
| Background tasks | Celery + Beat | 5.4+ | Voice EMAS (voice — async views); only cron/push |
| HTTP client | httpx | 0.28+ | Async support, `httpx.AsyncClient` for Gemini |
| Voice AI | google-genai SDK | 0.7+ | Gemini `gemini-2.0-flash` (audio + intent single call) |
| Bot | python-telegram-bot | 21.6+ | Webhook mode (NOT polling in production) |
| Frontend interaction | htmx | 2.0 | Server-rendered HTML swap |
| Frontend state | Alpine.js | 3.14 | Modal/dropdown state ONLY — major state yo'q |
| CSS | Tailwind CSS | 4.0 | CLI build, no Node app build chain |
| Settings env | python-decouple | 3.8+ | `.env` orqali, decouple secrets |
| Tests | pytest + pytest-django + pytest-asyncio | latest | factory-boy fixtures |
| Lint/format | ruff | 0.7+ | Single tool (lint + format), pre-commit |
| Template lint | djlint | latest | pre-commit |
| Reverse proxy / TLS | Caddy | 2.x | Auto Let's Encrypt |
| Hosting | Single VPS + Managed Postgres | — | Hetzner / Neon / Supabase |

**Dependency rules:**
- New dependency adding — justify in commit message (`feat: add httpx — needed for async Gemini calls`)
- No dependencies for things doable in stdlib (e.g., no `python-dateutil` if `datetime` yetadi)
- Pin major + minor in `requirements.txt`, allow patch (`Django>=5.1,<5.2`)

---

## Critical Implementation Rules

### Language-Specific Rules (Python)

**Type hints majburiy** har public function va class method'da:
```python
def create_transaction(*, user: User, type: TransactionType, amount: Decimal) -> Transaction: ...
```

**Keyword-only arguments** har xil tipdagi argument'lar uchun:
```python
def transfer(*, sender: User, receiver: User, amount: Decimal) -> None: ...  # ✅
def transfer(sender, receiver, amount): ...                                    # ❌ confusable
```

**`Decimal` import bir joydan** — `from decimal import Decimal`. **Hech qachon `float` ishlatma money uchun.** Voice parser Gemini'dan string oladi, `Decimal(value)` bilan konversiya qiladi.

**Async/sync mix:**
- Sync view'lar (manual transactions, debts, settings) — standart Django views
- Async view'lar (voice endpoints) — Django 5.1 `async def` views
- Async view ichida ORM chaqirilsa **`sync_to_async`** wrapper'da bo'lishi kerak (Django 5.1 ORM async limited):
  ```python
  from asgiref.sync import sync_to_async
  user = await sync_to_async(User.objects.get)(telegram_id=tg_id)
  ```
- Yangi Django ORM async methods (`aget`, `acreate`) afzal — qachon mavjud bo'lsa

**Exception hierarchy** har app'da `<app>/exceptions.py`:
```python
class TransactionError(Exception): pass
class InvalidAmountError(TransactionError): pass
```
**Hech qachon bare `Exception` raise qilma.** **Hech qachon bare `except:` ishlatma** — `except SomeError as e:` har doim.

**`logger.exception` vs `logger.warning`:**
- `logger.exception(msg)` — unexpected error, full traceback
- `logger.warning(msg)` — handled/expected error case
- `logger.info(msg)` — domain event (transaction created, debt closed)
- Never `print()` in production code

**Imports order** (ruff isort enforce qiladi):
1. stdlib
2. third-party
3. Django
4. local apps (each on its own group)
```python
from decimal import Decimal              # stdlib
from datetime import datetime, timezone

import httpx                              # third-party

from django.db import models              # django

from core.models import TimestampedModel  # local
from accounts.models import User
```

**Path / URL imports:** never hardcode URLs in code. Use `reverse('transactions:add')` or `{% url ... %}` in templates.

### Framework-Specific Rules (Django)

**Domain-driven apps** — har FR kategoriya bitta app'da yashaydi. App nomi: lowercase, plural domain noun (`transactions`, `debts`, `currencies`). Cross-app communication faqat `services.py` / `selectors.py` interface orqali.

**Services / Selectors / Views split (SOLID):**
- `services.py` — write operations (create, update, transition)
- `selectors.py` — read queries (filters, aggregations)
- `views.py` — thin orchestration: validate → call service/selector → render
- `models.py` — data + simple invariants only (constraints, default factories)
- **Business logic in models or views — anti-pattern.** Refactor immediately.

**Custom managers** for common queries:
```python
class TransactionManager(models.Manager):
    def for_user(self, user):
        return self.filter(user=user, is_deleted=False)
    def in_period(self, start, end):
        return self.filter(date__gte=start, date__lte=end)
```
Then: `Transaction.objects.for_user(user).in_period(start, end)` — readable, reusable.

**`@db_transaction.atomic`** har bir multi-step write'da. Voice multi-tx save — single atomic block.

**Migrations:**
- Generate via `python manage.py makemigrations <app>`
- Review migrations before merge — never edit migration after merge
- Squash before each major version release
- Data migrations alohida fayl (`migrations/0042_data_seed_categories.py` with `RunPython`)
- **Never** reset migrations on shared branches

**URLs:**
- Per-app `urls.py` with `app_name = 'transactions'`
- Root `iwallet/urls.py` includes them via `path('app/transactions/', include('transactions.urls', namespace='transactions'))`
- Path style: `kebab-case` for URL paths, `snake_case` for URL `name`
- Use `path()` with type converters (`<int:id>`, `<slug:slug>`) — not `re_path`

**Templates:**
- App-scoped: `<app>/templates/<app>/<view>.html`
- Partials prefix `_`: `_transaction_card.html` — never rendered alone
- `{% extends 'base.html' %}` for full pages
- htmx partial responses — no `extends`, just the fragment

**Settings:**
- **Single `iwallet/settings.py`** — no base/dev/prod split. Env-driven via `python-decouple`.
- `DJANGO_SETTINGS_MODULE=iwallet.settings` in `manage.py`, `wsgi.py`, `asgi.py`
- Secrets + dev/prod toggles from `.env` (gitignored): `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, `DATABASE_URL`, `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`. Never `os.environ` direct.
- `DEBUG = config('DEBUG', default=False, cast=bool)` — dev `.env` sets True, prod `.env` sets False
- `ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())` — strict, no wildcard in prod
- Conditional logic (HSTS, structured logging, etc.) inside `if not DEBUG:` blocks — keeps everything in one file, easy to reason about

**Forms:**
- Use `django.forms.Form` or `ModelForm`
- Validation in `clean_<field>()` and `clean()` methods
- HTML rendering via custom template (Tailwind classes, mobile-first)
- htmx forms have `hx-post` + `hx-target` attributes

**Auth — Telegram WebApp:**
- `TelegramAuthMiddleware` ON for `/app/*` routes only
- Per request: parse `X-Telegram-InitData` header → HMAC validate → get_or_create User → `request.user = user`
- Never persist Django session for WebApp endpoints (stateless)
- `request.user.is_authenticated` always True on `/app/*` (middleware ensures)
- Bot routes use different auth (Telegram bot token in webhook URL)

### htmx Patterns

**Response by endpoint type:**
- Full page (rare) — `render(...)` with `extends 'base.html'`
- htmx swap — `render(..., template_name='app/_partial.html')` returning just the fragment
- Redirect — `HttpResponse(headers={'HX-Redirect': '/app/home/'})`

**Trigger custom events** to client:
```python
return HttpResponse(content='', headers={
    'HX-Trigger': json.dumps({
        'toast': {'type': 'success', 'message': 'Tranzaksiya saqlandi'},
        'balanceUpdated': {'newAmount': '500000', 'currency': 'UZS'},
    }),
})
```

**Loading indicators:** use `hx-indicator="#voice-loading"` + Tailwind animated skeleton. **No spinner GIFs.**

**Anti-pattern:** putting Django context dict in `<script>` JSON for Alpine to consume. Use `data-*` attributes instead:
```html
<div x-data="{ amount: $el.dataset.amount }" data-amount="{{ tx.amount }}">
```

### Voice Pipeline Rules

**Audio handling:**
- **Read into memory, never to disk:** `audio_bytes = request.FILES['audio'].read()` then discard
- Pass bytes to Gemini SDK directly
- Audio bytes ko'rinmasligi kerak request logger'da — Django middleware audio endpoint'i uchun body logging'ni o'chiradi

**Gemini client:**
- Use `httpx.AsyncClient` lifecycle managed via `async with`
- Single client instance per request (no global client v1)
- Retry: 3x exponential backoff (0.5s, 1s, 2s) via `tenacity` or hand-rolled
- Timeout: 30s total per voice request

**Voice schema (Pydantic-style):**
```python
from dataclasses import dataclass
from decimal import Decimal
from datetime import date

@dataclass
class VoiceDraft:
    type: str  # 'expense' | 'income' | 'debt_lent' | 'debt_borrowed'
    amount: Decimal
    currency: str  # 'UZS' | 'RUB' | 'USD'
    category_slug: str
    counterparty: str | None
    date: date
    note: str | None
    confidence: float  # 0-1
    ambiguous_fields: list[str]
```

**Confidence threshold:** `confidence < 0.7` OR `ambiguous_fields not empty` → UI flags uncertain (FR24).

**Multi-transaction parsing:** Gemini prompt returns `list[VoiceDraft]` — even single tx wrapped in 1-item list. Confirm screen template iterates uniformly.

**Recurring intent detection:** Gemini response has `recurring_intent: VoiceDraft | None`. If present, UI offers "create recurring" action.

### Testing Rules

**Coverage target:** ≥80% on services and selectors. Views light coverage OK (integration tests).

**Test layout:** co-located in `<app>/tests/`:
```
transactions/tests/
├── conftest.py        # pytest fixtures (user, category)
├── factories.py       # factory-boy
├── test_models.py
├── test_services.py
├── test_selectors.py
├── test_views.py
└── test_integration.py
```

**Factories** via factory-boy:
```python
class TransactionFactory(DjangoModelFactory):
    class Meta:
        model = Transaction
    user = factory.SubFactory(UserFactory)
    amount = factory.Faker('pydecimal', positive=True, min_value=100, max_value=1000000)
    currency = 'UZS'
    type = 'expense'
```

**Test naming:** `test_<what_happens>_when_<condition>`:
```python
def test_create_transaction_raises_invalid_amount_when_amount_is_zero(): ...
def test_close_debt_transitions_to_partial_when_repayment_less_than_total(): ...
```

**Async tests** with `pytest.mark.asyncio`:
```python
@pytest.mark.asyncio
async def test_transcribe_returns_draft_when_audio_valid(mock_gemini_response):
    ...
```

**Mock external APIs only** — Gemini, CBU.uz, Telegram. **Never mock DB.** Use real Postgres test DB (pytest-django creates one).

**Voice mocking pattern:**
```python
@pytest.fixture
def mock_gemini_client(monkeypatch):
    async def fake_call(audio, user):
        return ParsedResponse(transactions=[...], recurring_intent=None)
    monkeypatch.setattr('voice.gemini_client.transcribe_and_parse', fake_call)
```

**No snapshot tests for HTML** v1 — fragile. Test rendered context, not exact HTML.

### Code Quality & Style Rules

**Ruff config** (`pyproject.toml`):
```toml
[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "DJ", "SIM", "RET", "ARG"]
ignore = ["E501"]  # line length handled by formatter

[tool.ruff.lint.isort]
known-first-party = ["accounts", "core", "transactions", "debts", "voice", "categories", "currencies", "recurring", "reports", "notifications"]
combine-as-imports = true
```

**Formatting:** `ruff format` enforced. 100 char line limit. **Double quotes** (Django + modern Python tooling convention; ruff format default).

**Naming summary:**
- `snake_case`: variables, functions, methods, modules, fields, URLs (`name=`)
- `PascalCase`: classes, dataclasses, models
- `UPPER_SNAKE_CASE`: constants
- `kebab-case`: URL paths, CSS classes (in `app.css` custom), HTML id
- `_leading_underscore`: private (module or class)

**No comments unless WHY non-obvious.** Code self-documents via clear names. Examples of allowed comments:
```python
# Telegram returns 64-bit ID, Django BigInt PK required
telegram_id = models.BigIntegerField(primary_key=True)

# CBU.uz returns 0.00 for unavailable currencies — treat as None
if Decimal(payload['rate']) == 0:
    return None
```

**Docstrings only on public services and complex selectors** — short, what + when, no `Args:/Returns:/Raises:` boilerplate unless really helpful:
```python
def create_transaction(*, user, type, amount, currency, category, date, note=None):
    """Create a transaction; raises InvalidAmountError if amount <= 0."""
```

**File length soft limit:** 300 lines per `.py` file. Beyond that, split. (Models can be longer if domain demands.)

**Template comments** sparingly: `{# Why this exists #}` — never `<!-- ... -->`.

### Development Workflow Rules

**Branch naming:** `<type>/<short-slug>`:
- `feat/voice-multi-tx-parsing`
- `fix/debt-partial-close-rounding`
- `chore/upgrade-django-5.1`
- `docs/update-readme`

**Commit messages** — conventional commits, but short:
```
feat(voice): multi-transaction parse with confidence threshold

Implements FR21 — Gemini returns multiple drafts in one call.
Confidence < 0.7 flags ambiguous fields for user edit.

Refs: PRD FR21, FR24
```

**PR checklist** (template in `.github/pull_request_template.md`):
- [ ] Linked story / FR ID
- [ ] Acceptance criteria met (paste AC list)
- [ ] Tests added/updated (coverage ≥80%)
- [ ] `ruff check` + `ruff format` + `djlint --check` green
- [ ] Migration reviewed (if any)
- [ ] No `print()`, no `float`, no `*` imports
- [ ] Telegram WebApp manual smoke test on iOS + Android

**Pre-commit hooks** (`.pre-commit-config.yaml`):
- `ruff check --fix`
- `ruff format`
- `djlint --reformat`
- `check-added-large-files` (>500KB block)
- `detect-private-key`

**CI** runs full `pytest --cov`, fails if coverage drops below baseline.

**Deployment:** GitHub Action on push to `main` → SSH deploy. No direct prod push. Rollback via flipping `current` symlink.

---

## Critical Don't-Miss Rules

### Money & Currency

🚨 **`float` taqiqlangan** — `Decimal` only for money. Even for ratios used in conversion.

🚨 **Hech qachon avtomatik valyuta konvertatsiyasi tranzaksiya saqlash paytida.** Storage — original currency. Display only — converted via CBU rate. Reports show per-currency breakdown.

🚨 **CBU.uz API ishlamasa** — eski (stale) kurs ishlatiladi, **tranzaksiyalar saqlanaveradi**. UI banner ko'rsatadi. Yangi tranzaksiya bloklanmaydi.

🚨 **Currency code 3-letter ISO** (`UZS`, `RUB`, `USD`) — har joyda. Hech qachon `сум`, `ruble`, `$` enum sifatida.

### Voice & Gemini

🚨 **Audio fayllar diskka yozilmaydi.** In-memory only. Logging'da audio body yozilmaydi.

🚨 **Gemini timeout 30s** — undan oshsa user'ga "yana urinish" alternative. Hech qachon infinite wait.

🚨 **Gemini response untrusted** — har field validate qil. `Decimal(payload['amount'])` ValueError beradi → graceful → "summa noaniq" UI flag.

🚨 **Voice endpoints async** (`async def`). Sync view'da `httpx.post` blocking — WSGI worker o'ldiradi.

🚨 **Gemini free tier 1500 req/day** — production monitoring kerak. Yaqinlashganda alert + Vertex AI fallback plan.

### Auth & Telegram

🚨 **`initData` HMAC har request'da revalidate** — middleware'da. Cache yo'q. `auth_date > 24h ago` → 401.

🚨 **Bot va WebApp alohida `User` model — yo'q.** Bitta `User`, `telegram_id` PK. Ikkala service shu DB'ga yozadi.

🚨 **Bot webhook URL'da secret token** — `https://example.com/bot/webhook/<random_secret>/`. URL guess'lash yo'l qo'yilmaydi.

🚨 **Deep-link payload** (`startapp` param) — Telegram limit 64 chars. Format `action_<type>__<id>` (max ~30 chars typical).

### Debt State Machine

🚨 **Qarz qaytarilishi yangi tranzaksiya yaratmaydi.** Bu `DebtRepayment` event'i, balansga aks ta'sir — hisoblanmaydi yangi income/expense sifatida (FR36). Double-counting'ni oldini olish kritik.

🚨 **Partial repayment** — qoldiq miqdor avtomatik hisoblanadi va `Debt.remaining_amount` field'da yangilanadi. Service: `apply_repayment(debt, amount)`.

🚨 **Boshqa valyutada qaytarish** — v1 da **ruxsat berilmaydi** (UI cheklaydi). Agar kerak bo'lsa v2'da hal qilamiz (kurs qaysi sanada?).

🚨 **Closed/cancelled debt'ni tahrirlash yo'q** — read-only. Yangi tranzaksiya yarat kerak bo'lsa.

### Database

🚨 **Soft delete only** transaction uchun (`is_deleted=True` + `deleted_at`). Hard delete v1 da yo'q (audit, undo uchun).

🚨 **N+1 query holatlarini oldini olish** — `select_related('user', 'category')` har FK access'da. `prefetch_related('repayments')` har reverse FK iteration'da.

🚨 **Index'lar shart**: `Transaction(user, date)`, `Transaction(user, type, date)`, `Debt(user, state)`. Slow queries (>50ms) — chuqurroq tekshir.

🚨 **Migration'lar prod'da downtime yaratmasligi kerak** — column add NOT NULL → bir migration default bilan, keyin to'ldirish, keyin NOT NULL constraint qo'shish. 3-step.

### Telegram WebApp

🚨 **Mobile viewport lock** — `<meta viewport>` aniq `width=device-width, initial-scale=1, maximum-scale=1`. User pinch-zoom o'chirilgan.

🚨 **Desktop'da ham mobile container** — `max-width: 430px` body container, atrofda slate-100 bg. Yangi UX'ga zarurat yo'q.

🚨 **Telegram BackButton bilan integratsiya** — har screen'da `window.Telegram.WebApp.BackButton.show()` (yoki `hide()`). Yo'qsa, kontrolsiz UX.

🚨 **MediaRecorder API iOS Safari** support cheklangan — `webm/opus` qabul qilmaydi, `mp4/aac` ishlatamiz. Fallback uchun detection kerak.

🚨 **Telegram WebApp lifecycle** — `closingConfirmation` enabled bo'lsin user ish jarayonida, save'dan keyin disable.

### Performance

🚨 **htmx swap latency 200ms target** — view'lar tezroq bo'lishi kerak. Slow → query optimization, caching, yoki htmx `hx-trigger="every Xs"` polling tashlash.

🚨 **Tailwind build size cap 30KB gzipped** — purge config to'g'ri, hech qachon `safelist` ko'p bo'lmasin.

🚨 **Async view ichida sync ORM** — `sync_to_async` wrap qilingan bo'lishi kerak. Aks holda silently blocking.

### Privacy & Security

🚨 **Logger'da PII yo'q** — full telegram_id loglamang (hash bilan). audio bytes — no. initData full string — no.

🚨 **CSP strict** — `default-src 'self'` + Telegram domains. Inline script'lar — nonce bilan (Django CSP middleware).

🚨 **Admin disabled in prod** — `urlpatterns` dan olib tashlanmagan bo'lsa, IP allow-list. Default — disabled.

🚨 **Rate limiting** — voice 10/min, manual 60/min, bot push send 100/min, per user. `django-ratelimit`.

### Edge Cases AI Agentlar Sezmaslik Mumkin

🚨 **Sana boundary** — "bugun" tushunchasi user timezone'ga bog'liq. Server UTC saqlaydi, display `Asia/Tashkent`. `now()` ishlatma — `django.utils.timezone.now()` ishlat.

🚨 **Zero amount** — manual form `min_value=0.01` Decimal validatsiya. Voice'da Gemini 0 qaytarsa → ambiguous flag.

🚨 **Negative amount** — never. Storage constraint `amount__gt=0`. Refund/return → `Income` tipi yangi tranzaksiya, original'ni tahrir emas.

🚨 **Future-dated transaction** — ruxsat berilmaydi v1 (PRD yo'q). Voice'da kelajak sana → bugunga clamp + warning.

🚨 **Currency mismatch** — debt'da counterparty `Akram USD 100` yozildi, qaytarish UZS'da — v1 da bloklanadi (yuqorida).

🚨 **Same-day repayment** — debt yaratildi va o'sha kuni qisman qaytarildi — state machine to'g'ri ishlamasligi mumkin. Test specifically.

🚨 **Recurring date drift** — har 1-chisi degan recurring, fevralda 29 oy? Default: oxirgi kun (28 fevral). Documented behavior.

🚨 **Onboarding skip** — agar user onboarding'ni o'tkazib yuborib darrov mic bossa — flow handle qilishi kerak (permission ask kontekst'da).

---

## Quick Reference — Top 10 Rules

1. **`Decimal` only for money, never `float`.**
2. **Voice endpoints async, ORM via `sync_to_async`.**
3. **Audio in-memory only, never disk, never log.**
4. **Services/Selectors/Views split — business logic in `services.py`.**
5. **`initData` HMAC validate every request, no session cache.**
6. **Debt repayment ≠ new transaction — separate event, no double-counting.**
7. **Soft delete, never hard delete v1.**
8. **htmx returns partials for swap, `HX-Redirect`/`HX-Trigger` for navigation/events.**
9. **Mobile viewport lock 430px max, no desktop layout.**
10. **CBU outage → stale rate + banner, never block UX.**

---

## When in Doubt

1. **Read `docs/architecture.md`** for full context
2. **Read `docs/prd.md`** for FR/NFR you're implementing
3. **Read `docs/ux-design-specification.md`** for UI/UX patterns
4. **Check `docs/epics.md`** for story acceptance criteria
5. **Search the codebase** for similar pattern before inventing new
6. **Ask Eric** if rule conflicts or genuinely ambiguous

Agentlar bu hujjatni session boshida o'qib chiqishi shart. Loyihada yangi qoida tug'ilsa — bu hujjat'ga qo'shiladi, code'da takrorlanmaydi.
