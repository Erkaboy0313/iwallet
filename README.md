# IWALLET

Telegram-native shaxsiy moliya trackeri — **ovoz orqali** kirim/chiqim yozadi, o'zbek tilida ishlaydi.

Foydalanuvchi Telegramda **@iwallet_uz_bot** ni ochib, WebApp'ga kiradi, mikrofonga gapiradi:

> «Nonga 25 ming sarfladim» / «Karimga 100 ming berdim» / «Bugun oyliq 5 million keldi»

Gemini AI ovozdan summa, kategoriya, sana, valyutani ajratib oladi. Ilova tasdiqlash kartochkalarini ko'rsatadi. Ha bosasiz — yoziladi.

## Nima qiladi

- 🎤 **Ovoz orqali tranzaksiya** — summa, kategoriya, sana, valyuta avtomatik
- 🤝 **Qarzlarni kuzatish** — kim qancha berib-olgani, Telegram bot orqali haftalik eslatma
- 🔁 **Takrorlanuvchi to'lovlar** — kunlik/haftalik/oylik prompt sifatida ("Bugun ijara qo'shamizmi?")
- 📊 **Hero split** — Sof balans (operating) + Olishingiz/Berishingiz alohida chip
- 💱 **3 valyuta** — UZS/USD/RUB, CBU.uz'dan avtomatik kurs
- 📈 **Oylik hisobot** — top xarajat kategoriyalari, kunlik oqim grafiklari

## Texnologiya

| Qatlam | Texnologiya |
|---|---|
| Backend | Django 5.2 (ASGI, async views for voice) |
| Frontend | htmx 2 + Alpine.js 3 + Tailwind 4 |
| DB | PostgreSQL 16 (prod) / SQLite (dev fallback) |
| Voice AI | Google Gemini 2.0 Flash (audio + intent) |
| Bot | python-telegram-bot 21+ (webhook mode) |
| Server | uvicorn (systemd) + nginx (reverse proxy + TLS via certbot) |
| Currency rates | CBU.uz JSON, session-gated daily refresh |
| Tests | pytest + pytest-django + factory-boy (603 test, 91% coverage) |

## Lokal dev

### Talablar

- Python 3.12+
- Node 22+ (Tailwind CLI)
- Docker Desktop (optional, PostgreSQL uchun — SQLite fallback ham ishlaydi)

### Boshlang'ich sozlash

```powershell
# 1. venv + Python deps
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt

# 2. .env yaratish
Copy-Item .env.example .env
# .env ichini to'ldiring:
#   SECRET_KEY=...
#   DEBUG=True
#   TELEGRAM_BOT_TOKEN=...
#   GEMINI_API_KEY=... (voice test uchun)

# 3. (ixtiyoriy) PostgreSQL Docker'da
docker-compose -f docker-compose.dev.yml up -d
# .env: DATABASE_URL=postgres://iwallet:iwallet_dev@localhost:5432/iwallet
# Yoki DATABASE_URL bo'sh qoldirsangiz — SQLite ishlaydi

# 4. Migratsiya + serverni ishga tushirish
python manage.py migrate
python manage.py createsuperuser  # admin uchun
uvicorn iwallet.asgi:application --reload --port 8000
```

Bot webhook lokalda ishlashi uchun **ngrok** yoki shunga o'xshash tunnel kerak.

### Tailwind CSS

```powershell
# Watch mode (dev)
npm run watch:css

# One-shot build (prod)
npm run build:css
```

### Testlar

```powershell
pytest -q                                  # butun suite
pytest --cov=. --cov-report=term-missing   # coverage bilan
pytest recurring/ voice/ -q                # bitta app
```

### Lint + format

```powershell
ruff check .        # Python lint
ruff format .       # Python format
djlint --check .    # Django template lint
```

Pre-commit hook'lar avtomatik ishlaydi commit paytida.

## Deployga chiqarish

Deploy diagrammasi va systemd/nginx yo'l-yo'riqlari: [deploy/README.md](deploy/README.md)

Qisqacha:
- GitHub Actions push'da CI ishga tushadi (test + rsync)
- Droplet'da `deploy.sh` migrate + collectstatic + symlink flip qiladi
- `iwallet-web.service` (uvicorn :8010) + `iwallet-bot.service` (uvicorn :8011) systemd'da yashaydi
- nginx `/bot/webhook/*` → :8011, qolgan hammasini :8010'ga proksilaydi

**Birinchi deploy'dan keyin bir marta:**

```bash
# Droplet'da:
cd /srv/iwallet/current
sudo -u iwallet /srv/iwallet/venv/bin/python manage.py setup_bot         # Telegram webhook + commands
sudo -u iwallet /srv/iwallet/venv/bin/python manage.py set_menu_button   # WebApp launch tugmasi
```

**Kunlik cron/timer'lar** (systemd timer bilan sozlanadi):

- `enqueue_debt_reminders` — 7 kundan eski qarzlar uchun bot xabari
- `send_pending_pushes` — PushQueueItem'larni Telegramga jo'natish
- `fetch_rates` (ixtiyoriy) — CBU.uz kurslarini kuniga yangilash

## Loyiha strukturasi

```
iwallet/            # Django project (settings, asgi, urls)
├── accounts/       # Telegram auth, User model
├── transactions/   # Kirim/chiqim/qarz yozuvlari (Transaction model)
├── categories/     # Foydalanuvchi kategoriyalari (income/expense)
├── debts/          # Qarz filtered viewlari (Transaction ustida)
├── recurring/      # Takrorlanuvchi to'lovlar + prompt flow
├── currencies/     # 3 valyuta, CBU.uz kurs, konvertatsiya
├── voice/          # Gemini integratsiyasi, transcribe + intent
├── reports/        # Oylik/haftalik hisobot ko'rinishlari
├── notifications/  # Bot handlerlari, webhook, PushQueueItem
├── quotes/         # Motivatsion iqtiboslar (kunlik quote)
└── core/           # Home, settings hub, umumiy templates + tokens.css
```

Har bir app ichida odatiy Django tuzilishi + `selectors.py` (read) va `services.py` (write) ajratilgan — ORM view'ga chiqmaydi.

## Rejalar

Batafsil planning: [docs/](docs/) (PRD, arxitektura, epics, sprint status)

## License

Xususiy loyiha. Litsenziya rasman berilmagan.
