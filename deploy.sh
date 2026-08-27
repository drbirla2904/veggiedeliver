#!/usr/bin/env bash
set -Eeuo pipefail

# One-file Ubuntu/Debian deployment for VeggieDeliver.
# Run as root from the project directory:
#   sudo bash deploy.sh example.com

if [[ $EUID -ne 0 ]]; then
  echo "Run this script as root: sudo bash deploy.sh your-domain.com" >&2
  exit 1
fi

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOMAIN="${1:-}"
APP_NAME="${APP_NAME:-veggiedeliver}"
DEPLOY_USER="${DEPLOY_USER:-${SUDO_USER:-${USER}}}"
DEPLOY_GROUP="${DEPLOY_GROUP:-www-data}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ -z "$DOMAIN" ]]; then
  echo "Usage: sudo bash deploy.sh your-domain.com" >&2
  exit 1
fi

if [[ "$DEPLOY_USER" == "root" ]]; then
  echo "Set DEPLOY_USER to the non-root Linux user that owns the project." >&2
  exit 1
fi

if [[ ! -f "$APP_DIR/manage.py" || ! -f "$APP_DIR/.env.example" ]]; then
  echo "Run this script from the Django project containing manage.py and .env.example." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y \
  build-essential \
  libpq-dev \
  nginx \
  postgresql \
  postgresql-contrib \
  redis-server \
  "$PYTHON_BIN" \
  "${PYTHON_BIN}-dev" \
  "${PYTHON_BIN}-venv"

if ! id "$DEPLOY_USER" >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash "$DEPLOY_USER"
fi

if [[ ! -f "$APP_DIR/.env" ]]; then
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  chmod 600 "$APP_DIR/.env"
  echo "Created $APP_DIR/.env from .env.example. Fill production values, then rerun this script."
  exit 0
fi

set -a
# shellcheck disable=SC1091
source "$APP_DIR/.env"
set +a

: "${DB_NAME:=veggiedeliver}"
: "${DB_USER:=veggiedeliver}"
: "${DB_PASSWORD:=}"
: "${DB_HOST:=127.0.0.1}"
: "${DB_PORT:=5432}"
: "${REDIS_URL:=redis://127.0.0.1:6379/0}"

if [[ "${DB_ENGINE:-postgres}" != "postgres" ]]; then
  echo "Production deployment requires DB_ENGINE=postgres in .env." >&2
  exit 1
fi
if [[ -z "$DB_PASSWORD" || "$DB_PASSWORD" == replace-with-* ]]; then
  echo "Set a real DB_PASSWORD in .env before deploying." >&2
  exit 1
fi
if [[ "${DJANGO_SECRET_KEY:-}" == "" || "${DJANGO_SECRET_KEY:-}" == replace-with-* ]]; then
  echo "Set a real DJANGO_SECRET_KEY in .env before deploying." >&2
  exit 1
fi

if ! id "$DEPLOY_USER" >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash "$DEPLOY_USER"
fi
usermod -aG "$DEPLOY_GROUP" "$DEPLOY_USER"

if [[ ! "$DB_NAME" =~ ^[A-Za-z_][A-Za-z0-9_]*$ || ! "$DB_USER" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
  echo "DB_NAME and DB_USER may contain only letters, numbers, and underscores." >&2
  exit 1
fi

if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1; then
  sudo -u postgres psql --set ON_ERROR_STOP=1 --set=db_password="$DB_PASSWORD" \
    -c "ALTER ROLE \"$DB_USER\" WITH LOGIN PASSWORD :'db_password';"
else
  sudo -u postgres psql --set ON_ERROR_STOP=1 --set=db_password="$DB_PASSWORD" \
    -c "CREATE ROLE \"$DB_USER\" LOGIN PASSWORD :'db_password';"
fi
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1; then
  sudo -u postgres createdb --owner="$DB_USER" "$DB_NAME"
fi

install -d -o "$DEPLOY_USER" -g "$DEPLOY_GROUP" "$APP_DIR/media" "$APP_DIR/staticfiles"
if [[ ! -x "$APP_DIR/venv/bin/python" ]]; then
  sudo -u "$DEPLOY_USER" "$PYTHON_BIN" -m venv "$APP_DIR/venv"
fi
sudo -u "$DEPLOY_USER" "$APP_DIR/venv/bin/pip" install --upgrade pip
sudo -u "$DEPLOY_USER" "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"
sudo -u "$DEPLOY_USER" env DJANGO_DEBUG=False "$APP_DIR/venv/bin/python" "$APP_DIR/manage.py" migrate --noinput
sudo -u "$DEPLOY_USER" env DJANGO_DEBUG=False "$APP_DIR/venv/bin/python" "$APP_DIR/manage.py" collectstatic --noinput
sudo -u "$DEPLOY_USER" env DJANGO_DEBUG=False "$APP_DIR/venv/bin/python" "$APP_DIR/manage.py" check --deploy

install -d -o "$DEPLOY_USER" -g "$DEPLOY_GROUP" "/run/$APP_NAME"

cat > "/etc/systemd/system/$APP_NAME.service" <<EOF
[Unit]
Description=$APP_NAME Gunicorn application
After=network.target postgresql.service redis-server.service

[Service]
User=$DEPLOY_USER
Group=$DEPLOY_GROUP
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
RuntimeDirectory=$APP_NAME
RuntimeDirectoryMode=0770
UMask=0007
ExecStart=$APP_DIR/venv/bin/gunicorn --workers 3 --timeout 120 --bind unix:/run/$APP_NAME/gunicorn.sock core.wsgi:application
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > "/etc/systemd/system/$APP_NAME-celery.service" <<EOF
[Unit]
Description=$APP_NAME Celery worker
After=network.target redis-server.service

[Service]
User=$DEPLOY_USER
Group=$DEPLOY_GROUP
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/celery -A core worker --loglevel=INFO --concurrency=2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > "/etc/systemd/system/$APP_NAME-celerybeat.service" <<EOF
[Unit]
Description=$APP_NAME Celery beat scheduler
After=network.target redis-server.service

[Service]
User=$DEPLOY_USER
Group=$DEPLOY_GROUP
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/celery -A core beat --loglevel=INFO
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > "/etc/nginx/sites-available/$APP_NAME" <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    client_max_body_size 20M;

    location /static/ {
        alias $APP_DIR/staticfiles/;
        expires 7d;
        add_header Cache-Control "public";
    }

    location /media/ {
        alias $APP_DIR/media/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/$APP_NAME/gunicorn.sock;
        proxy_read_timeout 120;
    }
}
EOF

ln -sfn "/etc/nginx/sites-available/$APP_NAME" "/etc/nginx/sites-enabled/$APP_NAME"
rm -f /etc/nginx/sites-enabled/default
nginx -t

systemctl daemon-reload
systemctl enable --now postgresql redis-server
systemctl enable --now "$APP_NAME.service" "$APP_NAME-celery.service" "$APP_NAME-celerybeat.service"
systemctl reload nginx || systemctl restart nginx

chown -R "$DEPLOY_USER:$DEPLOY_GROUP" "$APP_DIR/media" "$APP_DIR/staticfiles"
chmod 600 "$APP_DIR/.env"

echo
echo "Deployment complete for $DOMAIN"
echo "Gunicorn: systemctl status $APP_NAME"
echo "Celery:   systemctl status $APP_NAME-celery $APP_NAME-celerybeat"
echo "Logs:     journalctl -u $APP_NAME -f"
echo "Next: configure DNS, then add HTTPS with: certbot --nginx -d $DOMAIN"