#!/usr/bin/env bash
# One-time bootstrap on OVH (run as root).
# Usage: bash /opt/beatlab/deploy/bootstrap.sh
set -euo pipefail

APP_ROOT=/opt/beatlab
APP_USER=beatlab
DB_NAME=beatlab
DB_USER=beatlab

if [[ ! -f "$APP_ROOT/manage.py" ]]; then
  echo "Copy the repo into $APP_ROOT first."
  exit 1
fi

echo "==> Linux user"
if ! id -u "$APP_USER" >/dev/null 2>&1; then
  useradd --system --home "$APP_ROOT" --shell /usr/sbin/nologin "$APP_USER"
fi

mkdir -p "$APP_ROOT" /var/www/certbot
chown -R "$APP_USER:$APP_USER" "$APP_ROOT"

if [[ ! -f "$APP_ROOT/.env" ]]; then
  echo "==> Creating .env"
  DB_PASS="$(openssl rand -hex 16)"
  SECRET="$(openssl rand -hex 32)"
  cat > "$APP_ROOT/.env" <<EOF
DEBUG=0
SECRET_KEY=${SECRET}
ALLOWED_HOSTS=hub.nynusoft.com,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://hub.nynusoft.com
DATABASE_URL=postgres://${DB_USER}:${DB_PASS}@127.0.0.1:5432/${DB_NAME}
EMAIL_HOST=smtp.hostinger.com
EMAIL_PORT=465
EMAIL_USE_SSL=true
EMAIL_USE_TLS=false
EMAIL_HOST_USER=info@nynusoft.com
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=BeatLab Hub <info@nynusoft.com>
IMAP_HOST=imap.hostinger.com
IMAP_PORT=993
EOF
  chmod 640 "$APP_ROOT/.env"
  chown "$APP_USER:$APP_USER" "$APP_ROOT/.env"
  echo "Wrote $APP_ROOT/.env"
fi

set -a
# shellcheck disable=SC1091
source "$APP_ROOT/.env"
set +a
DB_PASS="${DATABASE_URL#*://beatlab:}"
DB_PASS="${DB_PASS%@127.0.0.1:5432/beatlab}"

echo "==> Postgres role/database"
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 \
  || sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 \
  || sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"
sudo -u postgres psql -c "ALTER USER ${DB_USER} WITH PASSWORD '${DB_PASS}';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"
sudo -u postgres psql -d "$DB_NAME" -c "GRANT ALL ON SCHEMA public TO ${DB_USER};"

echo "==> Python venv"
if [[ ! -x "$APP_ROOT/venv/bin/pip" ]]; then
  python3 -m venv "$APP_ROOT/venv"
fi
"$APP_ROOT/venv/bin/pip" install --upgrade pip
"$APP_ROOT/venv/bin/pip" install -r "$APP_ROOT/requirements.txt"
chown -R "$APP_USER:$APP_USER" "$APP_ROOT/venv"

if [[ -x "$(command -v npm)" && -f "$APP_ROOT/frontend/package.json" ]]; then
  echo "==> Frontend"
  (cd "$APP_ROOT/frontend" && npm ci && npm run build)
fi

echo "==> Migrate + collectstatic + admin"
chown -R "$APP_USER:$APP_USER" "$APP_ROOT"
if [[ -f "$APP_ROOT/.env" ]]; then
  chown "$APP_USER:$APP_USER" "$APP_ROOT/.env"
  chmod 640 "$APP_ROOT/.env"
fi
sudo -u "$APP_USER" env DJANGO_SETTINGS_MODULE=config.settings \
  "$APP_ROOT/venv/bin/python" "$APP_ROOT/manage.py" migrate --noinput
sudo -u "$APP_USER" env DJANGO_SETTINGS_MODULE=config.settings \
  "$APP_ROOT/venv/bin/python" "$APP_ROOT/manage.py" collectstatic --noinput
sudo -u "$APP_USER" env DJANGO_SETTINGS_MODULE=config.settings \
  "$APP_ROOT/venv/bin/python" "$APP_ROOT/manage.py" bootstrap_admin
if [[ -f "$APP_ROOT/.bootstrap-admin" ]]; then
  chown root:root "$APP_ROOT/.bootstrap-admin"
  chmod 600 "$APP_ROOT/.bootstrap-admin"
fi

echo "==> systemd"
cp "$APP_ROOT/deploy/beatlab.service" /etc/systemd/system/beatlab.service
systemctl daemon-reload
systemctl enable --now beatlab
systemctl restart beatlab

echo "==> nginx"
cp "$APP_ROOT/deploy/nginx-hub.conf" /etc/nginx/sites-available/hub
ln -sfn /etc/nginx/sites-available/hub /etc/nginx/sites-enabled/hub
nginx -t
systemctl reload nginx

echo "==> Done. Hub en https://hub.nynusoft.com"
if [[ -f "$APP_ROOT/.bootstrap-admin" ]]; then
  echo "Credenciales iniciales en $APP_ROOT/.bootstrap-admin"
fi
