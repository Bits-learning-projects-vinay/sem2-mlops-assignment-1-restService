#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/model-service}"
APP_USER="${APP_USER:-ubuntu}"
PORT="${PORT:-8000}"

if [[ -z "${MODEL_S3_BUCKET:-}" || -z "${MODEL_S3_KEY:-}" ]]; then
  echo "MODEL_S3_BUCKET and MODEL_S3_KEY must be set"
  exit 1
fi

sudo mkdir -p "$APP_DIR"
sudo chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

cd "$APP_DIR"
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

cat > .env <<EOF
MODEL_S3_BUCKET=${MODEL_S3_BUCKET}
MODEL_S3_KEY=${MODEL_S3_KEY}
MODEL_S3_REGION=${MODEL_S3_REGION:-ap-south-1}
PORT=${PORT}
EOF

sudo tee /etc/systemd/system/model-service.service >/dev/null <<EOF
[Unit]
Description=Flask model service
After=network.target

[Service]
Type=simple
User=${APP_USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/.venv/bin/gunicorn --workers 2 --bind 0.0.0.0:${PORT} model_service:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable model-service
sudo systemctl restart model-service
sudo systemctl status --no-pager model-service

