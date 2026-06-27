"""Sprint 0 — Story 0.8 — deploy artifacts sanity checks (no actual deploy)."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def test_nginx_config_exists_and_references_ports() -> None:
    nginx = (BASE_DIR / "deploy" / "nginx" / "iwallet.conf").read_text(encoding="utf-8")
    assert "proxy_pass http://127.0.0.1:8010" in nginx, "WebApp upstream not configured"
    assert "proxy_pass http://127.0.0.1:8011" in nginx, "Bot upstream not configured"
    assert "/healthz" in nginx
    assert "Strict-Transport-Security" in nginx
    assert "alias /srv/iwallet/current/staticfiles/" in nginx


def test_bootstrap_script_creates_postgres_and_nginx() -> None:
    boot = (BASE_DIR / "deploy" / "scripts" / "bootstrap-droplet.sh").read_text(encoding="utf-8")
    assert "set -euo pipefail" in boot
    assert "CREATE USER iwallet" in boot
    assert "CREATE DATABASE iwallet" in boot
    assert "nginx -t" in boot
    assert "iwallet-web.service" in boot


def test_all_systemd_units_present() -> None:
    units = BASE_DIR / "deploy" / "systemd"
    expected = {
        "iwallet-web.service",
        "iwallet-bot.service",
        "iwallet-celery-worker.service",
        "iwallet-celery-beat.service",
    }
    found = {p.name for p in units.iterdir() if p.suffix == ".service"}
    assert expected.issubset(found), f"Missing units: {expected - found}"


def test_systemd_web_unit_runs_uvicorn() -> None:
    web = (BASE_DIR / "deploy" / "systemd" / "iwallet-web.service").read_text(encoding="utf-8")
    assert "uvicorn iwallet.asgi:application" in web
    assert "EnvironmentFile=/srv/iwallet/shared/.env" in web


def test_deploy_script_is_atomic_symlink_flip() -> None:
    deploy = (BASE_DIR / "deploy" / "scripts" / "deploy.sh").read_text(encoding="utf-8")
    assert "set -euo pipefail" in deploy
    assert "ln -sfn" in deploy
    assert "mv -Tf" in deploy, "Symlink flip must be atomic via mv -Tf"
    assert "manage.py migrate" in deploy
    assert "manage.py collectstatic" in deploy


def test_deploy_workflow_uses_ssh_agent_and_healthcheck() -> None:
    wf = (BASE_DIR / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
    assert "webfactory/ssh-agent" in wf
    assert "/healthz" in wf
    assert "rsync" in wf
