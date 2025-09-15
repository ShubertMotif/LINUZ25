#!/bin/bash

# multi_flask_setup.sh - Setup per due app Flask in background con systemd

# Colori
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. CREAZIONE STRUTTURA PER DUE APP
setup_dual_apps() {
    log "📁 Creazione struttura per due app Flask..."

    # Crea directory per le due app
    mkdir -p /home/flaskapp/app1
    mkdir -p /home/flaskapp/app2
    mkdir -p /var/log/flask

    chown -R flaskapp:flaskapp /home/flaskapp
    chown -R flaskapp:flaskapp /var/log/flask

    log "✅ Directory create"
}

# 2. SETUP APP 1 (es. Adelchi Group)
setup_app1() {
    log "🐍 Setup App 1 (Adelchi Group)..."

    # Crea virtual environment per app1
    sudo -u flaskapp bash << 'EOF'
cd /home/flaskapp/app1
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install flask flask-sqlalchemy flask-login gunicorn python-dotenv
pip freeze > requirements.txt
EOF

    # Crea app1.py
    sudo -u flaskapp tee /home/flaskapp/app1/app.py > /dev/null << 'EOF'
from flask import Flask, render_template
from flask_login import LoginManager, current_user

app = Flask(__name__)
app.secret_key = 'adelchi_secret_2025'

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)

@app.context_processor
def inject_user():
    return dict(current_user=current_user)

@app.route('/')
def home():
    return '''
    <html>
    <head>
        <title>Adelchi Group</title>
        <style>
            body { font-family: Arial; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                   color: white; text-align: center; padding: 50px; min-height: 100vh; margin: 0; }
            .container { background: rgba(255,255,255,0.1); padding: 40px; border-radius: 20px;
                        backdrop-filter: blur(10px); max-width: 800px; margin: 0 auto; }
            h1 { font-size: 3em; margin-bottom: 20px; }
            .status { background: rgba(40,167,69,0.3); padding: 20px; border-radius: 10px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏢 Adelchi Group</h1>
            <div class="status">
                <h2>✅ App 1 - Running on Port 5001</h2>
                <p>Servizio principale Adelchi Group</p>
            </div>
            <p><strong>Servizi:</strong> Life Science | IT Services | Difesa | Finanza</p>
            <p><a href="/health" style="color: #FFD700;">Health Check</a></p>
        </div>
    </body>
    </html>
    '''

@app.route('/health')
def health():
    return {'status': 'healthy', 'app': 'adelchi-group', 'port': 5001}

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5001)
EOF

    log "✅ App 1 (Adelchi Group) creata"
}

# 3. SETUP APP 2 (es. TreasuryLootBox)
setup_app2() {
    log "🎮 Setup App 2 (TreasuryLootBox)..."

    # Crea virtual environment per app2
    sudo -u flaskapp bash << 'EOF'
cd /home/flaskapp/app2
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install flask flask-sqlalchemy flask-login gunicorn python-dotenv
pip freeze > requirements.txt
EOF

    # Crea app2.py
    sudo -u flaskapp tee /home/flaskapp/app2/app.py > /dev/null << 'EOF'
from flask import Flask, jsonify
import random

app = Flask(__name__)
app.secret_key = 'treasury_secret_2025'

@app.route('/')
def home():
    return '''
    <html>
    <head>
        <title>TreasuryLootBox</title>
        <style>
            body { font-family: Arial; background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
                   color: white; text-align: center; padding: 50px; min-height: 100vh; margin: 0; }
            .container { background: rgba(255,255,255,0.05); padding: 40px; border-radius: 20px;
                        backdrop-filter: blur(10px); max-width: 800px; margin: 0 auto;
                        border: 1px solid rgba(255,255,255,0.1); }
            h1 { font-size: 3em; margin-bottom: 20px; background: linear-gradient(45deg, #f59e0b, #3b82f6);
                 -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
            .status { background: rgba(245,158,11,0.2); padding: 20px; border-radius: 10px; margin: 20px 0;
                     border: 1px solid rgba(245,158,11,0.3); }
            .box { background: rgba(59,130,246,0.2); padding: 15px; border-radius: 10px; margin: 10px;
                   display: inline-block; border: 1px solid rgba(59,130,246,0.3); }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎮 TreasuryLootBox</h1>
            <div class="status">
                <h2>✅ App 2 - Running on Port 5002</h2>
                <p>Servizio finanziario gaming</p>
            </div>
            <div>
                <div class="box">📦 Common Box - €50</div>
                <div class="box">💎 Rare Box - €200</div>
                <div class="box">🏆 Epic Box - €500</div>
                <div class="box">👑 Legendary Box - €1000</div>
            </div>
            <p><a href="/health" style="color: #f59e0b;">Health Check</a> |
               <a href="/api/boxes" style="color: #3b82f6;">API Boxes</a></p>
        </div>
    </body>
    </html>
    '''

@app.route('/health')
def health():
    return {'status': 'healthy', 'app': 'treasury-lootbox', 'port': 5002}

@app.route('/api/boxes')
def api_boxes():
    boxes = [
        {'name': 'Common Box', 'price': 50, 'rarity': 'common'},
        {'name': 'Rare Box', 'price': 200, 'rarity': 'rare'},
        {'name': 'Epic Box', 'price': 500, 'rarity': 'epic'},
        {'name': 'Legendary Box', 'price': 1000, 'rarity': 'legendary'}
    ]
    return jsonify(boxes)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5002)
EOF

    log "✅ App 2 (TreasuryLootBox) creata"
}

# 4. CREAZIONE SERVIZI SYSTEMD
create_systemd_services() {
    log "⚙️ Creazione servizi systemd..."

    # Servizio per App 1
    tee /etc/systemd/system/adelchi-app.service > /dev/null << 'EOF'
[Unit]
Description=Adelchi Group Flask App
After=network.target

[Service]
Type=exec
User=flaskapp
Group=flaskapp
WorkingDirectory=/home/flaskapp/app1
Environment=PATH=/home/flaskapp/app1/venv/bin
Environment=FLASK_ENV=production
ExecStart=/home/flaskapp/app1/venv/bin/python app.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/flask/adelchi.log
StandardError=append:/var/log/flask/adelchi-error.log

[Install]
WantedBy=multi-user.target
EOF

    # Servizio per App 2
    tee /etc/systemd/system/treasury-app.service > /dev/null << 'EOF'
[Unit]
Description=TreasuryLootBox Flask App
After=network.target

[Service]
Type=exec
User=flaskapp
Group=flaskapp
WorkingDirectory=/home/flaskapp/app2
Environment=PATH=/home/flaskapp/app2/venv/bin
Environment=FLASK_ENV=production
ExecStart=/home/flaskapp/app2/venv/bin/python app.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/flask/treasury.log
StandardError=append:/var/log/flask/treasury-error.log

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd
    systemctl daemon-reload

    log "✅ Servizi systemd creati"
}

# 5. CONFIGURAZIONE NGINX PER DUE APP
configure_nginx_dual() {
    log "🌐 Configurazione Nginx per due app..."

    # Configurazione Nginx con reverse proxy
    tee /etc/nginx/sites-available/dual-flask > /dev/null << 'EOF'
# App 1 - Adelchi Group (porta 80)
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /home/flaskapp/app1/static;
        expires 30d;
    }
}

# App 2 - TreasuryLootBox (porta 8080)
server {
    listen 8080;
    listen [::]:8080;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /home/flaskapp/app2/static;
        expires 30d;
    }
}
EOF

    # Abilita configurazione
    rm -f /etc/nginx/sites-enabled/default
    ln -sf /etc/nginx/sites-available/dual-flask /etc/nginx/sites-enabled/

    # Test e ricarica Nginx
    nginx -t && systemctl reload nginx

    log "✅ Nginx configurato per due app"
}

# 6. SCRIPT DI GESTIONE
create_management_scripts() {
    log "📝 Creazione script di gestione..."

    # Script principale di controllo
    tee /home/flaskapp/manage_apps.sh > /dev/null << 'EOF'
#!/bin/bash

# manage_apps.sh - Gestione delle due app Flask

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

case "$1" in
    start)
        echo -e "${GREEN}🚀 Avvio di entrambe le app...${NC}"
        sudo systemctl start adelchi-app
        sudo systemctl start treasury-app
        sleep 2
        ;;
    stop)
        echo -e "${RED}🛑 Arresto di entrambe le app...${NC}"
        sudo systemctl stop adelchi-app
        sudo systemctl stop treasury-app
        ;;
    restart)
        echo -e "${YELLOW}🔄 Riavvio di entrambe le app...${NC}"
        sudo systemctl restart adelchi-app
        sudo systemctl restart treasury-app
        sleep 2
        ;;
    status)
        echo -e "${GREEN}📊 Status delle app:${NC}"
        echo ""
        echo "App 1 - Adelchi Group:"
        sudo systemctl is-active adelchi-app
        echo "App 2 - TreasuryLootBox:"
        sudo systemctl is-active treasury-app
        echo ""
        echo "URLs:"
        SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "localhost")
        echo "  📱 App 1: http://$SERVER_IP"
        echo "  🎮 App 2: http://$SERVER_IP:8080"
        ;;
    logs)
        case "$2" in
            1|adelchi)
                echo -e "${GREEN}📋 Log App 1 (Adelchi):${NC}"
                sudo journalctl -u adelchi-app -f
                ;;
            2|treasury)
                echo -e "${GREEN}📋 Log App 2 (Treasury):${NC}"
                sudo journalctl -u treasury-app -f
                ;;
            *)
                echo "Usa: $0 logs [1|2|adelchi|treasury]"
                ;;
        esac
        ;;
    enable)
        echo -e "${GREEN}✅ Abilito avvio automatico...${NC}"
        sudo systemctl enable adelchi-app
        sudo systemctl enable treasury-app
        ;;
    disable)
        echo -e "${YELLOW}❌ Disabilito avvio automatico...${NC}"
        sudo systemctl disable adelchi-app
        sudo systemctl disable treasury-app
        ;;
    test)
        SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "localhost")
        echo -e "${GREEN}🔍 Test connessioni:${NC}"
        echo ""
        echo "App 1 Health:"
        curl -s http://$SERVER_IP/health | jq . 2>/dev/null || curl -s http://$SERVER_IP/health
        echo ""
        echo "App 2 Health:"
        curl -s http://$SERVER_IP:8080/health | jq . 2>/dev/null || curl -s http://$SERVER_IP:8080/health
        ;;
    *)
        echo "Uso: $0 {start|stop|restart|status|logs|enable|disable|test}"
        echo ""
        echo "Comandi:"
        echo "  start     - Avvia entrambe le app"
        echo "  stop      - Ferma entrambe le app"
        echo "  restart   - Riavvia entrambe le app"
        echo "  status    - Mostra stato delle app"
        echo "  logs [1|2] - Mostra log (1=Adelchi, 2=Treasury)"
        echo "  enable    - Abilita avvio automatico"
        echo "  disable   - Disabilita avvio automatico"
        echo "  test      - Testa connessioni"
        ;;
esac
EOF

    chmod +x /home/flaskapp/manage_apps.sh
    chown flaskapp:flaskapp /home/flaskapp/manage_apps.sh

    # Crea symlink per accesso facile
    ln -sf /home/flaskapp/manage_apps.sh /usr/local/bin/flask-apps

    log "✅ Script di gestione creati"
}

# 7. AVVIO SERVIZI
start_services() {
    log "🚀 Avvio servizi..."

    # Abilita e avvia servizi
    systemctl enable adelchi-app
    systemctl enable treasury-app
    systemctl start adelchi-app
    systemctl start treasury-app

    sleep 3

    # Verifica stato
    if systemctl is-active --quiet adelchi-app && systemctl is-active --quiet treasury-app; then
        log "✅ Entrambe le app sono attive"
    else
        error "⚠️ Problema con uno o entrambi i servizi"
    fi
}

# 8. APERTURA PORTE FIREWALL
configure_firewall() {
    log "🔥 Configurazione firewall..."

    ufw allow 80/tcp
    ufw allow 8080/tcp
    ufw allow 5001/tcp  # Direct access se necessario
    ufw allow 5002/tcp  # Direct access se necessario

    log "✅ Porte aperte: 80, 8080, 5001, 5002"
}

# 9. TEST FINALE
test_setup() {
    log "🧪 Test setup finale..."

    SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "localhost")

    echo ""
    echo "🔍 Test connessioni:"

    # Test App 1
    if curl -s http://$SERVER_IP/health > /dev/null; then
        echo "✅ App 1 (Adelchi): OK"
    else
        echo "❌ App 1 (Adelchi): FAIL"
    fi

    # Test App 2
    if curl -s http://$SERVER_IP:8080/health > /dev/null; then
        echo "✅ App 2 (Treasury): OK"
    else
        echo "❌ App 2 (Treasury): FAIL"
    fi

    echo ""
}

# RIEPILOGO FINALE
show_final_summary() {
    SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "TUO_IP")

    echo ""
    echo "🎉 SETUP DUAL FLASK COMPLETATO!"
    echo ""
    echo "📱 App 1 - Adelchi Group:"
    echo "   🌐 http://$SERVER_IP"
    echo "   🩺 http://$SERVER_IP/health"
    echo ""
    echo "🎮 App 2 - TreasuryLootBox:"
    echo "   🌐 http://$SERVER_IP:8080"
    echo "   🩺 http://$SERVER_IP:8080/health"
    echo "   📊 http://$SERVER_IP:8080/api/boxes"
    echo ""
    echo "🎛️ Gestione app:"
    echo "   flask-apps start       # Avvia entrambe"
    echo "   flask-apps stop        # Ferma entrambe"
    echo "   flask-apps restart     # Riavvia entrambe"
    echo "   flask-apps status      # Stato app"
    echo "   flask-apps logs 1      # Log App 1"
    echo "   flask-apps logs 2      # Log App 2"
    echo "   flask-apps test        # Test connessioni"
    echo ""
    echo "📁 File app:"
    echo "   App 1: /home/flaskapp/app1/app.py"
    echo "   App 2: /home/flaskapp/app2/app.py"
    echo ""
    echo "📜 Log:"
    echo "   sudo journalctl -u adelchi-app -f"
    echo "   sudo journalctl -u treasury-app -f"
    echo ""
    echo "✨ Le app ripartiranno automaticamente al riavvio del server!"
}

# MAIN EXECUTION
main() {
    echo "🚀 Setup Dual Flask Apps con Systemd"
    echo "🎯 Niente più screen - Gestione automatica in background"
    echo ""

    if [ "$EUID" -ne 0 ]; then
        error "Esegui come root: sudo ./multi_flask_setup.sh"
        exit 1
    fi

    setup_dual_apps
    setup_app1
    setup_app2
    create_systemd_services
    configure_nginx_dual
    create_management_scripts
    start_services
    configure_firewall
    test_setup
    show_final_summary

    echo "🎉 Setup completato! Le tue app girano in background!"
}

main "$@"