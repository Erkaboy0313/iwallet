#!/usr/bin/env bash
# One-time droplet bootstrap for IWALLET.
# Run as a sudoer user (NOT iwallet) on a fresh Ubuntu 24.04 droplet.
# Idempotent: safe to re-run.

set -euo pipefail

DOMAIN="${IWALLET_DOMAIN:?Set IWALLET_DOMAIN, e.g. iwallet.buildermode.uz}"
DB_PASSWORD="${IWALLET_DB_PASSWORD:?Set IWALLET_DB_PASSWORD to a strong random string}"

echo "→ Bootstrapping IWALLET on $(hostname) for ${DOMAIN}"

# 1. System packages (Python 3.12 from Ubuntu 24.04 default repos — consistent with other projects on this droplet)
sudo apt update
sudo apt install -y \
    python3 python3-venv python3-dev \
    build-essential libpq-dev \
    nodejs npm \
    postgresql-16 postgresql-contrib \
    redis-server \
    rsync

# 2. iwallet user + dirs
if ! id iwallet &>/dev/null; then
    sudo adduser --disabled-password --system --group iwallet
fi
sudo mkdir -p /srv/iwallet/{releases,shared/logs}
sudo chown -R iwallet:iwallet /srv/iwallet

# 3. Persistent Python venv (uses system python3 = 3.12 on Ubuntu 24.04)
if [[ ! -d /srv/iwallet/venv ]]; then
    sudo -u iwallet python3 -m venv /srv/iwallet/venv
fi

# 4. Local Postgres DB + user
sudo -u postgres psql <<SQL
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'iwallet') THEN
        CREATE USER iwallet WITH PASSWORD '${DB_PASSWORD}';
    END IF;
END\$\$;
SELECT 'CREATE DATABASE iwallet OWNER iwallet'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'iwallet')\gexec
ALTER DATABASE iwallet OWNER TO iwallet;
SQL

# 5. Redis enabled (uses DB 1 to coexist with any other project on DB 0)
sudo systemctl enable --now redis-server

# 6. nginx server block install + reload (domain already hardcoded to ${DOMAIN} in repo)
sudo cp deploy/nginx/iwallet.conf /etc/nginx/sites-available/iwallet
if [[ ! -L /etc/nginx/sites-enabled/iwallet ]]; then
    sudo ln -s /etc/nginx/sites-available/iwallet /etc/nginx/sites-enabled/iwallet
fi
sudo nginx -t
sudo systemctl reload nginx

# 7. systemd web unit install (bot + celery enabled later)
sudo cp deploy/systemd/iwallet-web.service /etc/systemd/system/
sudo systemctl daemon-reload
# enable but don't start yet — needs .env + first release
sudo systemctl enable iwallet-web.service

echo ""
echo "✓ Bootstrap complete."
echo ""
echo "Next steps (manual):"
echo "  1. Place /srv/iwallet/shared/.env (chmod 600, owner iwallet)"
echo "     DATABASE_URL=postgres://iwallet:${DB_PASSWORD}@localhost:5432/iwallet"
echo "     REDIS_URL=redis://localhost:6379/1   # DB 1 to avoid clash with existing project"
echo "     TELEGRAM_BOT_TOKEN=..."
echo "     SECRET_KEY=..."
echo "     DEBUG=False  ALLOWED_HOSTS=${DOMAIN}"
echo "  2. Add SSH public key for 'iwallet' user (used by GitHub Actions deploy)."
echo "  3. Push to GitHub main → deploy workflow runs."
echo "  4. After first deploy succeeds:"
echo "     sudo certbot --nginx -d ${DOMAIN}"
echo "     sudo systemctl start iwallet-web.service"
