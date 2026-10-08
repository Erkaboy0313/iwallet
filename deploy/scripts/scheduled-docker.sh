#!/usr/bin/env bash
set -euo pipefail
RELEASE_DIR="$(readlink -f /srv/iwallet/current)"
export IWALLET_RELEASE="$(basename "$RELEASE_DIR")"
compose=(docker compose -f "$RELEASE_DIR/deploy/docker/compose.yml")
case "${1:?usage: scheduled-docker.sh pushes|rates|daily|backup}" in
    pushes)
        "${compose[@]}" exec -T web python manage.py send_pending_pushes
        ;;
    rates)
        "${compose[@]}" exec -T web python manage.py fetch_rates
        ;;
    daily)
        "${compose[@]}" exec -T web python manage.py enqueue_debt_reminders
        ;;
    backup)
        umask 077
        mkdir -p /srv/iwallet/shared/backups
        target="/srv/iwallet/shared/backups/daily-$(date -u +%Y%m%dT%H%M%SZ).dump"
        "${compose[@]}" exec -T db pg_dump -U iwallet -d iwallet -Fc > "$target.tmp"
        mv "$target.tmp" "$target"
        ;;
    *) exit 2 ;;
esac
