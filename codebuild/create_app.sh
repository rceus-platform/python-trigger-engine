#!/usr/bin/env bash
set -euo pipefail

# ================================
# REQUIRED ENV
# ================================
APP_NAME="${APP_NAME:?APP_NAME not set}"
APP_SECRET_PATH="${APP_SECRET_PATH:?APP_SECRET_PATH not set}"
GITHUB_REPOSITORY="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY not set}"

# ================================
# CONSTANTS
# ================================
BASE_DIR="/opt/apps"
APP_DIR="$BASE_DIR/$APP_NAME"
SECRETS_DIR="/opt/secrets"
DEPLOY_USER="ubuntu"

MANIFEST="$APP_DIR/codebuild/app.manifest.json"

# ================================
# PREP
# ================================
echo "➡ Creating app: $APP_NAME"

cd "$APP_DIR"

# ================================
# CLONE REPO
# ================================
if [ ! -d ".git" ]; then
  echo "📥 Cloning repository"
  git clone "https://github.com/${GITHUB_REPOSITORY}" .
else
  echo "📦 Repository already exists"
fi

# ================================
# READ MANIFEST
# ================================
if [ ! -f "$MANIFEST" ]; then
  echo "❌ Missing codebuild/app.manifest.json"
  exit 1
fi

RUNTIME=$(jq -r '.runtime' "$MANIFEST")
WORKDIR=$(jq -r '.working_dir' "$MANIFEST")
START_CMD=$(jq -r '.start_command' "$MANIFEST")
PORT=$(jq -r '.port' "$MANIFEST")
DOMAIN=$(jq -r '.domain' "$MANIFEST")

APP_WORKDIR="$APP_DIR/$WORKDIR"

if [ ! -d "$APP_WORKDIR" ]; then
  echo "❌ working_dir does not exist: $APP_WORKDIR"
  exit 1
fi

cd "$APP_WORKDIR"

# ================================
# RUNTIME SETUP
# ================================
if [ "$RUNTIME" = "python" ]; then
  echo "🐍 Setting up Python runtime"
  python3 -m venv .venv
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install -r requirements.txt

  if [ -f manage.py ]; then
    echo "🗄️ Running Django migrations (SQLite creation)"
    .venv/bin/python manage.py migrate --noinput
  fi
fi

if [ "$RUNTIME" = "node" ]; then
  echo "🟢 Setting up Node runtime"
  npm install
  npm run build || true
fi

if [ "$RUNTIME" = "go" ]; then
  echo "🐹 Building Go binary"
  go build -o app
fi

if [ "$RUNTIME" = "java" ]; then
  echo "☕ Java runtime assumed (no build step)"
fi

# ================================
# SYSTEMD SERVICE
# ================================
echo "⚙ Creating systemd service"

cat > "/etc/systemd/system/${APP_NAME}.service" <<EOF
[Unit]
Description=${APP_NAME}
After=network.target

[Service]
User=${DEPLOY_USER}
WorkingDirectory=${APP_WORKDIR}
Environment=APP_SECRET_JSON=${APP_SECRET_PATH}
ExecStart=${APP_WORKDIR}/${START_CMD}
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "${APP_NAME}"
systemctl restart "${APP_NAME}"

# ================================
# NGINX CONFIG
# ================================
echo "🌐 Configuring nginx"

cat > "/etc/nginx/sites-available/${DOMAIN}" <<EOF
server {
  listen 80;
  server_name ${DOMAIN};

  location / {
    proxy_pass http://127.0.0.1:${PORT};
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
  }
}
EOF

ln -sf "/etc/nginx/sites-available/${DOMAIN}" "/etc/nginx/sites-enabled/${DOMAIN}"
nginx -t
systemctl reload nginx

echo "✅ App creation complete"
