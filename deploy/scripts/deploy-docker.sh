#!/usr/bin/env bash
# Run as root: bash /srv/iwallet/releases/<release>/deploy/scripts/deploy-docker.sh <release>
set -euo pipefail
umask 077
APP_ROOT=/srv/iwallet
RELEASE="${1:?usage: deploy-docker.sh <release>}"
[[ "$RELEASE" =~ ^[a-zA-Z0-9_-]+$ ]] || { echo 'Invalid release'; exit 1; }
RELEASE_DIR="$APP_ROOT/releases/$RELEASE"
test -f "$RELEASE_DIR/deploy/docker/compose.yml"
test -s "$APP_ROOT/shared/.env"
test -s "$APP_ROOT/shared/db.env"
exec 9>"$APP_ROOT/shared/deploy.lock"
flock -n 9 || { echo 'Another deployment is running'; exit 1; }
export IWALLET_RELEASE="$RELEASE"
compose=(docker compose -f "$RELEASE_DIR/deploy/docker/compose.yml")

"${compose[@]}" config --quiet
"${compose[@]}" build web gateway
"${compose[@]}" up -d --wait db
mkdir -p "$APP_ROOT/shared/backups"
BACKUP="$APP_ROOT/shared/backups/pre-deploy-$(date -u +%Y%m%dT%H%M%SZ).dump"
"${compose[@]}" exec -T db pg_dump -U iwallet -d iwallet -Fc > "$BACKUP"
"${compose[@]}" run --rm --no-deps web python manage.py check --deploy --fail-level WARNING
"${compose[@]}" run --rm --no-deps web python manage.py migrate --noinput
"${compose[@]}" up -d --wait --wait-timeout 180
ln -sfn "$RELEASE_DIR" "$APP_ROOT/current.new"
mv -Tf "$APP_ROOT/current.new" "$APP_ROOT/current"
# Keep background jobs in sync with the release that serves requests.
install -m 644 "$RELEASE_DIR/deploy/systemd/iwallet-docker@.service" /etc/systemd/system/
for job in pushes rates daily backup; do
    install -m 644 "$RELEASE_DIR/deploy/systemd/iwallet-$job.timer" /etc/systemd/system/
done
systemctl daemon-reload
systemctl enable --now iwallet-pushes.timer iwallet-rates.timer iwallet-daily.timer iwallet-backup.timer
echo "Deployed $RELEASE; pre-migration backup: $BACKUP"
