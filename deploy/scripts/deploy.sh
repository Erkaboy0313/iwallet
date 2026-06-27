#!/usr/bin/env bash
# Deploy a new release of IWALLET on the production VPS.
# Invoked by .github/workflows/deploy.yml via SSH.
# Idempotent + safe: only flips the `current` symlink at the very end.

set -euo pipefail

APP_ROOT=/srv/iwallet
SHA="${1:?usage: deploy.sh <git-sha>}"
RELEASE_DIR="${APP_ROOT}/releases/${SHA}"

echo "→ Deploying ${SHA} to ${RELEASE_DIR}"

# 1. Sync code (assumed already rsynced to ${RELEASE_DIR} by the workflow)
test -d "${RELEASE_DIR}" || { echo "FATAL: ${RELEASE_DIR} missing"; exit 1; }

# 2. Link shared .env
ln -sfn "${APP_ROOT}/shared/.env" "${RELEASE_DIR}/.env"

# 3. Install Python deps in shared venv (recreate if Python upgraded)
"${APP_ROOT}/venv/bin/pip" install -r "${RELEASE_DIR}/requirements.txt"

# 4. Build Tailwind CSS (Tailwind is a devDependency — install all deps, not --omit=dev)
cd "${RELEASE_DIR}"
npm ci
npm run build:css

# 5. Migrate DB (safe — fail aborts before symlink flip)
"${APP_ROOT}/venv/bin/python" manage.py migrate --noinput

# 6. Collect static
"${APP_ROOT}/venv/bin/python" manage.py collectstatic --noinput

# 7. Flip symlink atomically
ln -sfn "${RELEASE_DIR}" "${APP_ROOT}/current.new"
mv -Tf "${APP_ROOT}/current.new" "${APP_ROOT}/current"

# 8. Restart services (nginx reloads only if config changed manually — not on every deploy)
sudo systemctl restart iwallet-web.service
# Bot + Celery units are restarted once they exist (Epics 5, 7, 9).
# sudo systemctl restart iwallet-bot.service iwallet-celery-worker.service iwallet-celery-beat.service

# 9. Prune old releases (keep last 5)
ls -1dt "${APP_ROOT}/releases/"*/ | tail -n +6 | xargs -r rm -rf

echo "✓ Deployed ${SHA}"
