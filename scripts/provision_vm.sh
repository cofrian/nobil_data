#!/usr/bin/env bash
set -euo pipefail

SERVICE_USER="nobil"
PROJECT_DIR="/opt/nobil-postgres-historico"
SERVICE_NAME="nobil-postgres-historico.service"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Este script debe ejecutarse como root (sudo)." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  apt-get update
  apt-get install -y python3 python3-venv python3-pip
fi

if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --home "$PROJECT_DIR" --create-home --shell /usr/sbin/nologin "$SERVICE_USER"
fi

mkdir -p "$PROJECT_DIR"
chown -R "$SERVICE_USER:$SERVICE_USER" "$PROJECT_DIR"

if [[ ! -f "$PROJECT_DIR/requirements.txt" ]]; then
  echo "No se encontro el codigo en $PROJECT_DIR. Copia el proyecto ahi y vuelve a ejecutar." >&2
  exit 1
fi

if [[ ! -d "$PROJECT_DIR/.venv" ]]; then
  sudo -u "$SERVICE_USER" python3 -m venv "$PROJECT_DIR/.venv"
fi

sudo -u "$SERVICE_USER" "$PROJECT_DIR/.venv/bin/pip" install --upgrade pip
sudo -u "$SERVICE_USER" "$PROJECT_DIR/.venv/bin/pip" install -r "$PROJECT_DIR/requirements.txt"

if [[ ! -f "$PROJECT_DIR/.env" ]]; then
  cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
fi

chmod 640 "$PROJECT_DIR/.env"
chown "$SERVICE_USER:$SERVICE_USER" "$PROJECT_DIR/.env"

NOBIL_API_KEY_VAL="$(grep -E '^NOBIL_API_KEY=' "$PROJECT_DIR/.env" | sed 's/^NOBIL_API_KEY=//')"
DATABASE_URL_VAL="$(grep -E '^DATABASE_URL=' "$PROJECT_DIR/.env" | sed 's/^DATABASE_URL=//')"

if [[ -z "$NOBIL_API_KEY_VAL" ]]; then
  echo "Falta NOBIL_API_KEY en $PROJECT_DIR/.env" >&2
  exit 2
fi

if [[ -z "$DATABASE_URL_VAL" ]]; then
  echo "Falta DATABASE_URL en $PROJECT_DIR/.env" >&2
  exit 2
fi

if [[ "$DATABASE_URL_VAL" != *"sslmode=require"* ]]; then
  echo "DATABASE_URL debe incluir sslmode=require" >&2
  exit 2
fi

install -m 644 "$PROJECT_DIR/nobil-postgres-historico.service" "/etc/systemd/system/$SERVICE_NAME"
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

systemctl --no-pager --full status "$SERVICE_NAME" | head -n 25
journalctl -u "$SERVICE_NAME" -n 50 --no-pager

echo "Provision finalizado."
