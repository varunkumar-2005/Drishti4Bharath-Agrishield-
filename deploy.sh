#!/bin/bash
# ══════════════════════════════════════════════════════════════
# AgroShield — EC2 Deployment Script
# Run on a fresh Ubuntu 22.04 EC2 t3.medium instance
# ══════════════════════════════════════════════════════════════

set -e

echo "══ AgroShield Deployment Starting ══"

# ── 1. System deps ────────────────────────────────────────────
sudo apt-get update -y
sudo apt-get install -y python3.11 python3.11-pip python3.11-venv \
     nginx nodejs npm git unzip awscli

# ── 2. Clone / copy project ───────────────────────────────────
cd /opt
sudo mkdir -p agroshield && sudo chown $USER:$USER agroshield
# (copy project files here or git clone your repo)

# ── 3. Backend setup ──────────────────────────────────────────
cd /opt/agroshield/backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Copy .env file (edit with your AWS credentials)
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠ Edit /opt/agroshield/backend/.env with your AWS credentials"
fi

# ── 4. Frontend build ─────────────────────────────────────────
cd /opt/agroshield/frontend
npm ci
npm run build

# Copy built files to nginx
sudo cp -r dist/* /var/www/html/
sudo chown -R www-data:www-data /var/www/html

# ── 5. Nginx config ───────────────────────────────────────────
sudo tee /etc/nginx/sites-available/agroshield <<'EOF'
server {
    listen 80;
    server_name _;

    root /var/www/html;
    index index.html;

    # Serve React frontend
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API to FastAPI backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/agroshield /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# ── 6. Systemd service for FastAPI ───────────────────────────
sudo tee /etc/systemd/system/agroshield.service <<EOF
[Unit]
Description=AgroShield FastAPI Backend
After=network.target

[Service]
User=$USER
WorkingDirectory=/opt/agroshield/backend
EnvironmentFile=/opt/agroshield/backend/.env
ExecStart=/opt/agroshield/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable agroshield
sudo systemctl start agroshield

echo "══ Deployment Complete ══"
echo "Backend:  http://localhost:8000"
echo "Frontend: http://$(curl -s ifconfig.me)"
echo ""
echo "Check backend logs: sudo journalctl -u agroshield -f"
