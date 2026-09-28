#!/bin/bash
set -e

DOMAIN="calendator.online"
EMAIL="max886066@gmail.com"
POSTGRES_PASSWORD="fdtA126_AsK"

GIT_USERNAME=""          
GIT_TOKEN=""             

GIT_REPO_BASE="https://github.com/pipipopy0/Calendator"
PROJECT_DIR="/root/Calendator"
STATIC_DIR="/var/www/calendator"

if [ -z "$GIT_USERNAME" ] || [ -z "$GIT_TOKEN" ]; then
    echo "🔐 Введите логин (username) для доступа к GitHub:"
    read -r GIT_USERNAME
    echo "🔐 Введите токен (Personal Access Token) для доступа к GitHub:"
    read -rs GIT_TOKEN
    echo ""
fi

GIT_REPO="https://${GIT_USERNAME}:${GIT_TOKEN}@github.com/pipipopy0/Calendator"

echo "🚀 Начинаем настройку сервера..."

apt update && apt upgrade -y
apt install -y \
    git curl wget \
    python3 python3-pip python3-venv \
    ffmpeg \
    postgresql postgresql-contrib \
    nginx \
    certbot python3-certbot-nginx \
    docker.io

systemctl enable --now docker
systemctl enable --now nginx

if [ ! -d "$PROJECT_DIR" ]; then
    echo "📦 Клонируем репозиторий..."
    git clone $GIT_REPO $PROJECT_DIR
else
    echo "✅ Репозиторий уже существует, обновляем..."
    cd $PROJECT_DIR
    git pull
fi
cd $PROJECT_DIR

if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "⚠️  Скопирован .env.example – отредактируй его позже!"
    else
        echo "❌ Нет .env.example – создай .env вручную!"
        exit 1
    fi
fi

sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD '$POSTGRES_PASSWORD';"

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

if ! docker ps -a --format '{{.Names}}' | grep -q duckling; then
    docker run -d \
        --name duckling \
        -p 8001:8000 \
        --restart always \
        rasa/duckling
else
    echo "✅ Duckling уже запущен"
fi

mkdir -p $STATIC_DIR
cp -r $PROJECT_DIR/SITE/* $STATIC_DIR/

cat > /etc/nginx/sites-available/calendator <<EOF
server {
    server_name $DOMAIN;
    root $STATIC_DIR;
    index index.html;

    location /callback {
        proxy_pass http://127.0.0.1:8005;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location / {
        try_files \$uri \$uri/ =404;
    }

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}

server {
    if (\$host = $DOMAIN) {
        return 301 https://\$host\$request_uri;
    }
    listen 80;
    server_name $DOMAIN;
    return 404;
}
EOF

ln -sf /etc/nginx/sites-available/calendator /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

certbot --nginx -d $DOMAIN \
    --non-interactive \
    --agree-tos \
    --email $EMAIL \
    --redirect

cat > /etc/systemd/system/main.service <<EOF
[Unit]
Description=Calendator Main
After=network.target postgresql.service docker.service

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/flask.service <<EOF
[Unit]
Description=Calendator Flask Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/services/flask_service.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now main.service flask.service

echo "============================================"
echo "✅ Настройка завершена!"
echo "🌐 Сайт: https://$DOMAIN"
echo "📝 Проверь .env, особенно REDIRECT_URI и EXCHANGE_RATE"
echo "🔐 Токен для GitHub не сохранён – он был использован только для клонирования."
echo "============================================"