# Deploy

Production deploy for IWALLET — single Linux droplet (DO/Hetzner), **nginx** reverse proxy, local Postgres + Redis, systemd-managed uvicorn services.

## Layout (on droplet)

```
/srv/iwallet/
├── current/      → symlink → releases/<sha>/
├── releases/
│   └── <sha>/    rsynced from CI; deploy.sh runs migrate + collectstatic, then flips symlink
├── shared/
│   ├── .env      production secrets (chmod 600, owner iwallet)
│   └── logs/
└── venv/         persistent Python 3.13 venv

/etc/nginx/sites-enabled/iwallet  → deploy/nginx/iwallet.conf
/etc/systemd/system/iwallet-*.service
```

## First-time droplet bootstrap

Eric's note: droplet already runs another project. IWALLET adds the `iwallet` user, `:8000` (web) + `:8001` (bot) ports, separate nginx server block, separate Postgres DB, **Redis DB 1** (to avoid clashing with anyone using DB 0).

### Automated path

```bash
# As a sudoer (not iwallet) on the droplet, with this repo cloned somewhere:
export IWALLET_DOMAIN=iwallet.buildermode.uz
export IWALLET_DB_PASSWORD=<generate-a-strong-random-string>
bash deploy/scripts/bootstrap-droplet.sh
```

The script is idempotent — re-runnable if a step fails.

### Manual equivalents (audit / debug)

```bash
# Packages (only those potentially missing — droplet already has nginx, etc.)
sudo apt update
sudo apt install -y python3.13 python3.13-venv build-essential libpq-dev nodejs npm postgresql-16 redis-server rsync

# Layout + user
sudo adduser --disabled-password --system --group iwallet
sudo mkdir -p /srv/iwallet/{releases,shared/logs}
sudo chown -R iwallet:iwallet /srv/iwallet
sudo -u iwallet python3.13 -m venv /srv/iwallet/venv

# Postgres local DB + user
sudo -u postgres psql -c "CREATE USER iwallet WITH PASSWORD 'STRONG-RANDOM';"
sudo -u postgres psql -c "CREATE DATABASE iwallet OWNER iwallet;"

# Redis already running for existing project — IWALLET uses DB 1 to coexist.

# nginx server block
sudo cp deploy/nginx/iwallet.conf /etc/nginx/sites-available/iwallet
# Edit and replace iwallet.buildermode.uz with the real subdomain.
sudo ln -s /etc/nginx/sites-available/iwallet /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# systemd unit
sudo cp deploy/systemd/iwallet-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable iwallet-web.service   # don't start yet — needs .env + first release
```

### Production `.env` (`/srv/iwallet/shared/.env`)

```env
SECRET_KEY=<50-char random — generate via: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
DEBUG=False
ALLOWED_HOSTS=iwallet.buildermode.uz
DATABASE_URL=postgres://iwallet:<DB_PASSWORD>@localhost:5432/iwallet
TELEGRAM_BOT_TOKEN=<from @BotFather>
TELEGRAM_WEBHOOK_SECRET=<random 32-char string — Epic 9 webhook URL component>
GEMINI_API_KEY=<from aistudio.google.com/apikey — optional until Story 2.3>
REDIS_URL=redis://localhost:6379/1
LOG_LEVEL=INFO
```

```bash
sudo chmod 600 /srv/iwallet/shared/.env
sudo chown iwallet:iwallet /srv/iwallet/shared/.env
```

### TLS (Let's Encrypt via certbot)

After the first deploy succeeds and HTTP works on `http://iwallet.buildermode.uz/healthz`:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d iwallet.buildermode.uz
# certbot rewrites the server block to add HTTPS + auto-renew cron.
```

## GitHub Actions secrets

Repo → Settings → Secrets and variables → Actions → New repository secret:

| Name | Value |
|---|---|
| `DEPLOY_SSH_KEY` | Private key (ed25519) authorized for `iwallet@droplet` |
| `DEPLOY_HOST` | droplet IP or `iwallet.buildermode.uz` |
| `DEPLOY_DOMAIN` | `iwallet.buildermode.uz` (used by healthcheck step) |

## Per-release flow

1. Push to `main` → CI runs (`.github/workflows/ci.yml`): lint + djlint + pytest.
2. On CI green, `.github/workflows/deploy.yml` rsyncs source to `/srv/iwallet/releases/<sha>/`.
3. SSH'd `deploy.sh` installs deps in the shared venv, builds Tailwind, migrates DB, runs collectstatic.
4. `current` symlink flipped atomically (`mv -Tf`).
5. `systemctl restart iwallet-web.service`.
6. Healthcheck: `curl https://iwallet.buildermode.uz/healthz` → `ok`.

## Rollback

```bash
ssh iwallet@droplet
ln -sfn /srv/iwallet/releases/<previous-sha> /srv/iwallet/current.new
mv -Tf /srv/iwallet/current.new /srv/iwallet/current
sudo systemctl restart iwallet-web.service
```
