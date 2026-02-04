#!/usr/bin/env bash
set -euo pipefail

# ==================================================
# GLOBAL CONFIG
# ==================================================
BASE_DIR="/opt/apps"
SECRETS_DIR="/opt/secrets"
NGINX_AVAILABLE="/etc/nginx/sites-available"
NGINX_ENABLED="/etc/nginx/sites-enabled"

DEPLOY_USER="ubuntu"
BASE_DOMAIN="rceus.duckdns.org"

PYTHON_BIN="/usr/bin/python3.10"

# ==================================================
# INPUT
# ==================================================
APP_NAME="$1"

if [[ -z "$APP_NAME" ]]; then
  echo "❌ Usage: create_app.sh <app-name>"
  exit 1
fi

# ==================================================
# DERIVED
# ==================================================
APP_DIR="$BASE_DIR/$APP_NAME"
SERVICE_NAME="$APP_NAME.service"
MANIFEST="$APP_DIR/app.manifest.json"

SUBDOMAIN="${APP_NAME#*-}"
DOMAIN="${SUBDOMAIN}.${BASE_DOMAIN}"

SECRET_FILE="$SECRETS_DIR/${APP_NAME}.json"

echo "=================================================="
echo "App name      : $APP_NAME"
echo "App dir       : $APP_DIR"
echo "Domain        : http://$DOMAIN"
echo "Secret file   : $SECRET_FILE"
echo "=================================================="

# ==================================================
# SAFETY
# ==================================================
if [[ -d "$APP_DIR" ]]; then
  echo "❌ App already exists: $APP_DIR"
  exit 1
fi

# ==================================================
# CLONE REPO
# ==================================================
mkdir -p "$APP_DIR"
chown -R "$DEPLOY_USER:$DEPLOY_USER" "$APP_DIR"

sudo -u "$DEPLOY_USER" git clone "https://github.com/rceus-platform/$APP_NAME.git" "$APP_DIR"

# ==================================================
# READ MANIFEST
# ==================================================
if [[ ! -f "$MANIFEST" ]]; then
  echo "❌ app.manifest.json missing"
  exit 1
fi

APP_TYPE=$(jq -r '.app_type' "$MANIFEST")
ENTRYPOINT=$(jq -r '.entrypoint' "$MANIFEST")
PORT=$(jq -r '.port' "$MANIFEST")
WORKERS=$(jq -r '.workers // 1' "$MANIFEST")
PROTOCOL=$(jq -r '.protocol // "asgi"' "$MANIFEST")

# ==================================================
# PYTHON ENV
# ==================================================
sudo -u "$DEPLOY_USER" "$PYTHON_BIN" -m venv "$APP_DIR/.venv"
sudo -u "$DEPLOY_USER" "$APP_DIR/.venv/bin/pip" install --upgrade pip
sudo -u "$DEPLOY_USER" "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

# ==================================================
# BUILD EXECSTART (ABSOLUTE PATH ONLY)
# ==================================================
if [[ "$APP_TYPE" == "django" ]]; then
  if [[ "$PROTOCOL" == "asgi" ]]; then
    CMD="$APP_DIR/.venv/bin/gunicorn ${ENTRYPOINT}.asgi:application -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:${PORT} --workers ${WORKERS}"
  else
    CMD="$APP_DIR/.venv/bin/gunicorn ${ENTRYPOINT}.wsgi:application --bind 127.0.0.1:${PORT} --workers ${WORKERS}"
  fi
elif [[ "$APP_TYPE" == "fastapi" ]]; then
  CMD="$APP_DIR/.venv/bin/uvicorn ${ENTRYPOINT} --host 127.0.0.1 --port ${PORT} --workers ${WORKERS}"
else
  echo "❌ Unknown app_type: $APP_TYPE"
  exit 1
fi

# ==================================================
# SYSTEMD SERVICE
# ==================================================
cat > "/etc/systemd/system/${SERVICE_NAME}" <<EOF
[Unit]
Description=${APP_NAME} Service
After=network.target

[Service]
User=${DEPLOY_USER}
WorkingDirectory=${APP_DIR}
Environment="APP_SECRET_JSON=${SECRET_FILE}"
ExecStart=${CMD}
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl restart "${SERVICE_NAME}"

# ==================================================
# NGINX (HTTP ONLY)
# ==================================================
NGINX_CONF="${NGINX_AVAILABLE}/${DOMAIN}"

cat > "$NGINX_CONF" <<EOF
server {
    listen 80;
    server_name ${DOMAIN};

    location / {
        proxy_pass http://127.0.0.1:${PORT};
        proxy_http_version 1.1;

        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

ln -sf "$NGINX_CONF" "${NGINX_ENABLED}/${DOMAIN}"

nginx -t
systemctl reload nginx

# ==================================================
# DONE
# ==================================================
echo "=================================================="
echo "✅ App deployed successfully"
echo "🌍 URL: http://${DOMAIN}"
echo "🩺 Health: http://${DOMAIN}/health"
echo "=================================================="
