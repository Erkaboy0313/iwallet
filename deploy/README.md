# IWALLET production deployment

Production: **https://track.hygen.uz**, server **217.76.61.147** (SSH alias `private`).

This server already hosts `narx` and `hygen`. Its public ports 80/443 belong to
`narx-web-1` (Caddy). Do not run the legacy host-nginx bootstrap here.

## Runtime

```text
Internet -> existing Caddy (TLS) -> iwallet-gateway:8080
                                    /static/ -> baked CSS/JS
                                    /bot/webhook/ -> bot:8011
                                    everything else -> web:8010
web + bot -> db:5432 (PostgreSQL 16, volume iwallet_postgres)
```

Only the gateway joins Caddy's existing `narx_default` Docker network. IWALLET
publishes no host ports. Web, bot and PostgreSQL share a separate Docker network.
The application currently uses management commands rather than Celery/Redis.

Source layout on the server:

```text
/srv/iwallet/releases/<release>/    source + Compose + Dockerfile
/srv/iwallet/current               symlink to the successful release
/srv/iwallet/shared/.env           application secrets (mode 600)
/srv/iwallet/shared/db.env         PostgreSQL credentials (mode 600)
/srv/iwallet/shared/backups/       pg_dump custom-format backups
/opt/caddy/sites/iwallet.caddy     imported by the existing Caddy
```

The initial deployment starts with a fresh database. The local `db.sqlite3` is
excluded from deployment. No data from the old server has been imported.

## Deploy a release

Upload source to a new `/srv/iwallet/releases/<release>/` directory, excluding
`.git`, `.env*`, `.venv`, `node_modules`, local databases and backups. Then, as root:

```bash
bash /srv/iwallet/releases/<release>/deploy/scripts/deploy-docker.sh <release>
```

The script builds Tailwind and the production images, starts PostgreSQL, takes a
database backup, runs Django production checks and migrations, then waits for all
four containers to become healthy before updating `current`, then installs and
enables the IWALLET timers. Runtime credentials
are not copied into the Docker images. Each release has its own image tags.

For the first deployment only, back up the existing Caddy site file outside the
`sites/*.caddy` glob, install `deploy/caddy/iwallet.caddy`, validate and reload:

```bash
docker exec narx-web-1 caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
docker exec narx-web-1 caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
```

Caddy obtains and renews TLS automatically. No host nginx or certbot is needed.

## Operations

Use the current release's image tag when invoking Compose:

```bash
cd /srv/iwallet/current
export IWALLET_RELEASE="$(basename "$(readlink -f /srv/iwallet/current)")"
docker compose -f deploy/docker/compose.yml ps
docker compose -f deploy/docker/compose.yml logs --tail=100 web bot
docker compose -f deploy/docker/compose.yml exec -T web python manage.py check --deploy
curl -fsS https://track.hygen.uz/healthz
```

After the first healthy HTTPS deployment, register the existing production bot:

```bash
docker compose -f deploy/docker/compose.yml exec -T web python manage.py setup_bot
docker compose -f deploy/docker/compose.yml exec -T web python manage.py set_menu_button
```

Install `iwallet-docker@.service`, `iwallet-pushes.timer`, `iwallet-rates.timer`,
`iwallet-daily.timer` and `iwallet-backup.timer` from `deploy/systemd/`. Enable the
four timers after the first successful deploy. They deliver queued notifications
every five minutes, refresh exchange rates hourly, queue debt reminders at 09:00
Tashkent time, and back up PostgreSQL at 03:00 Tashkent time. Exchange-rate network
requests never run while rendering a page. Docker restarts the application containers
after reboot. These are the only IWALLET systemd units needed for Docker deploys.

## Backups and later import

Create an extra backup at any time:

```bash
bash /srv/iwallet/current/deploy/scripts/scheduled-docker.sh backup
```

Backups live in `/srv/iwallet/shared/backups/`; copy important backups off-server.
The PostgreSQL volume survives container and image replacement. Never use
`docker compose down -v` against production.

When the old server's database becomes available, first identify its engine and
schema and test the dump in a separate database. Then pause IWALLET timers and
writers, take a fresh backup, restore/import the old data, apply migrations, check
record counts and resume services. PostgreSQL custom-format dumps use
`pg_restore`; SQLite requires an application-level data migration. Do not feed
a SQLite file to PostgreSQL or automatically overwrite production data.

Application rollback uses the previous release's image tags and Compose file.
Check migration compatibility first: the deploy script does not automatically
reverse migrations or restore data after a failed release. A failed migration or
healthcheck exits nonzero and requires investigation; `current` is not advanced.

## GitHub Actions

The deployment workflow builds Docker images on this server after successful CI
for a push to `main`, once repository variable `DEPLOY_ENABLED` is set to `true`.
Keep it disabled until the deployment account and all secrets below are ready:

- `DEPLOY_HOST`: `217.76.61.147`
- `DEPLOY_SSH_KEY`: key for a deployment account with the required Docker and
  `/srv/iwallet` access (the initial manual deployment uses root)
- `DEPLOY_KNOWN_HOSTS`: independently verified SSH host-key line(s)
- `DEPLOY_DOMAIN`: `track.hygen.uz`

Repository variable `DEPLOY_USER` defaults to `root`. The manual deployment does
not install SSH private keys or configure GitHub repository secrets. A deploy
account with Docker access effectively has root privileges.

The old `deploy/nginx/iwallet.conf`, `bootstrap-droplet.sh`, `deploy.sh`, and
uvicorn/Celery service units are retained for reference; they are not the active
deployment path for this host.
