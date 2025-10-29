#!/bin/bash

# ubuntu_flask_setup.sh - Setup completo Ubuntu 22.04/24.04 per Flask
# Per server DigitalOcean 2GB RAM, 50GB SSD

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Verifica che sia Ubuntu
check_ubuntu() {
    if ! grep -q "Ubuntu" /etc/os-release; then
        error "Questo script è per Ubuntu. Sistema rilevato: $(cat /etc/os-release | grep PRETTY_NAME)"
    fi

    UBUNTU_VERSION=$(lsb_release -rs)
    log "✅ Ubuntu $UBUNTU_VERSION rilevato"
}

# 1. AGGIORNAMENTO SISTEMA
update_system() {
    log "📦 Aggiornamento sistema Ubuntu..."

    # Update package list
    apt update

    # Upgrade existing packages
    apt upgrade -y

    # Install essential packages
    apt install -y \
        curl \
        wget \
        git \
        vim \
        nano \
        htop \
        tree \
        unzip \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        gnupg \
        lsb-release

    log "✅ Sistema aggiornato"
}

# 2. INSTALLAZIONE PYTHON
install_python() {
    log "🐍 Installazione Python e strumenti..."

    # Install Python 3.12 (latest)
    apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        python3-setuptools \
        python3-wheel \
        build-essential \
        libffi-dev \
        libssl-dev \
        libbz2-dev \
        libreadline-dev \
        libsqlite3-dev \
        libncurses5-dev \
        libncursesw5-dev \
        xz-utils \
        tk-dev \
        libxml2-dev \
        libxmlsec1-dev \
        libffi-dev \
        liblzma-dev

    # Crea symlink per python (opzionale)
    if ! command -v python &> /dev/null; then
        ln -sf /usr/bin/python3 /usr/bin/python
        log "✅ Symlink python3 -> python creato"
    fi

    # Upgrade pip
    python3 -m pip install --upgrade pip

    # Verifica installazione
    PYTHON_VERSION=$(python3 --version)
    PIP_VERSION=$(pip3 --version)

    log "✅ $PYTHON_VERSION installato"
    log "✅ $PIP_VERSION installato"
}

# 3. INSTALLAZIONE NGINX
install_nginx() {
    log "🌐 Installazione Nginx..."

    apt install -y nginx

    # Avvia e abilita Nginx
    systemctl start nginx
    systemctl enable nginx

    # Verifica stato
    if systemctl is-active --quiet nginx; then
        log "✅ Nginx installato e attivo"
    else
        warning "⚠️ Nginx installato ma non attivo"
    fi
}

# 4. CONFIGURAZIONE FIREWALL
setup_firewall() {
    log "🔥 Configurazione firewall UFW..."

    # Abilita UFW
    ufw --force enable

    # Regole base
    ufw default deny incoming
    ufw default allow outgoing

    # Porte essenziali
    ufw allow ssh
    ufw allow 'Nginx Full'
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw allow 8080/tcp    # Per sviluppo Flask

    # Mostra stato
    ufw status verbose

    log "✅ Firewall configurato"
}

# 5. INSTALLAZIONE NODE.JS (per strumenti frontend)
install_nodejs() {
    log "📦 Installazione Node.js..."

    # Install NodeSource repository
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -

    # Install Node.js
    apt install -y nodejs

    # Verifica installazione
    NODE_VERSION=$(node --version)
    NPM_VERSION=$(npm --version)

    log "✅ Node.js $NODE_VERSION installato"
    log "✅ npm $NPM_VERSION installato"
}

# 6. INSTALLAZIONE DATABASE
install_databases() {
    log "🗄️ Installazione database..."

    # SQLite (incluso con Python)
    apt install -y sqlite3

    # PostgreSQL (opzionale ma raccomandato)
    read -p "Vuoi installare PostgreSQL? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        apt install -y postgresql postgresql-contrib libpq-dev
        systemctl start postgresql
        systemctl enable postgresql
        log "✅ PostgreSQL installato"

        # Crea database per Flask
        sudo -u postgres createdb flaskapp
        sudo -u postgres psql -c "CREATE USER flaskuser WITH PASSWORD 'flask123';"
        sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE flaskapp TO flaskuser;"
        log "✅ Database 'flaskapp' creato"
    fi

    # Redis (per cache e sessioni)
    read -p "Vuoi installare Redis? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        apt install -y redis-server
        systemctl start redis-server
        systemctl enable redis-server
        log "✅ Redis installato"
    fi
}

# 7. CREAZIONE UTENTE PER APP (security best practice)
create_app_user() {
    log "👤 Creazione utente per applicazione..."

    # Crea utente dedicato (non root per sicurezza)
    if ! id "flaskapp" &>/dev/null; then
        useradd -m -s /bin/bash flaskapp
        usermod -aG www-data flaskapp
        log "✅ Utente 'flaskapp' creato"
    else
        log "✅ Utente 'flaskapp' già esistente"
    fi

    # Crea directory app
    mkdir -p /home/flaskapp/app
    chown -R flaskapp:flaskapp /home/flaskapp

    log "✅ Directory app creata"
}

# 8. INSTALLAZIONE CERTIFICATI SSL
install_certbot() {
    log "🔒 Installazione Certbot per SSL..."

    # Install snapd
    apt install -y snapd

    # Install certbot via snap
    snap install core; snap refresh core
    snap install --classic certbot

    # Create symlink
    ln -sf /snap/bin/certbot /usr/bin/certbot

    log "✅ Certbot installato"
}

# 9. CREAZIONE AMBIENTE FLASK
create_flask_environment() {
    log "🐍 Creazione ambiente Flask..."

    # Cambia all'utente flask
    sudo -u flaskapp bash << 'EOFFLASK'
    cd /home/flaskapp/app

    # Crea virtual environment
    python3 -m venv venv
    source venv/bin/activate

    # Upgrade pip nel venv
    pip install --upgrade pip

    # Install Flask e dipendenze comuni
    pip install \
        flask \
        flask-sqlalchemy \
        flask-login \
        flask-wtf \
        flask-migrate \
        gunicorn \
        python-dotenv \
        requests \
        psycopg2-binary \
        redis \
        celery \
        pillow \
        python-decouple

    # Crea requirements.txt
    pip freeze > requirements.txt

    echo "✅ Virtual environment creato in /home/flaskapp/app/venv"
EOFFLASK

    log "✅ Ambiente Flask configurato"
}

# 10. CREAZIONE APP FLASK DI TEST
create_test_app() {
    log "🧪 Creazione app Flask di test..."

    # Crea app di test
    sudo -u flaskapp tee /home/flaskapp/app/app.py > /dev/null << 'EOF'
from flask import Flask, render_template, jsonify
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

@app.route('/')
def home():
    return render_template('index.html',
                         server_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'python_version': '3.x',
        'flask_version': 'latest'
    })

@app.route('/info')
def info():
    return jsonify({
        'server': 'Ubuntu + Flask',
        'python': 'Python 3.x',
        'database': 'SQLite/PostgreSQL',
        'webserver': 'Nginx + Gunicorn',
        'ssl': 'Let\'s Encrypt'
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
EOF

    # Crea directory templates
    sudo -u flaskapp mkdir -p /home/flaskapp/app/templates

    # Crea template di test
    sudo -u flaskapp tee /home/flaskapp/app/templates/index.html > /dev/null << 'EOF'
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Flask Server Ready!</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            text-align: center;
            max-width: 800px;
            padding: 2rem;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            backdrop-filter: blur(10px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }
        h1 {
            font-size: 3rem;
            margin-bottom: 1rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .status {
            background: rgba(40, 167, 69, 0.2);
            padding: 1rem;
            border-radius: 10px;
            margin: 2rem 0;
            border: 1px solid rgba(40, 167, 69, 0.5);
        }
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 2rem 0;
        }
        .info-card {
            background: rgba(255, 255, 255, 0.1);
            padding: 1rem;
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .btn {
            display: inline-block;
            background: rgba(255, 255, 255, 0.2);
            color: white;
            padding: 1rem 2rem;
            text-decoration: none;
            border-radius: 50px;
            margin: 0.5rem;
            transition: all 0.3s ease;
            border: 2px solid rgba(255, 255, 255, 0.3);
        }
        .btn:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
        }
        code {
            background: rgba(0, 0, 0, 0.3);
            padding: 0.2rem 0.5rem;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎉 Flask Server Ready!</h1>

        <div class="status">
            <h2>✅ Server Ubuntu Configurato con Successo</h2>
            <p>Il tuo server è pronto per sviluppare applicazioni Flask</p>
            <p><strong>Server Time:</strong> {{ server_time }}</p>
        </div>

        <div class="info-grid">
            <div class="info-card">
                <h3>🐍 Python</h3>
                <p>Python 3.x + pip</p>
                <p>Virtual environment attivo</p>
            </div>
            <div class="info-card">
                <h3>🌐 Flask</h3>
                <p>Framework installato</p>
                <p>Pronto per lo sviluppo</p>
            </div>
            <div class="info-card">
                <h3>🗄️ Database</h3>
                <p>SQLite + PostgreSQL</p>
                <p>Redis per cache</p>
            </div>
            <div class="info-card">
                <h3>🔒 Sicurezza</h3>
                <p>Nginx + SSL ready</p>
                <p>Firewall configurato</p>
            </div>
        </div>

        <div>
            <a href="/health" class="btn">🏥 Health Check</a>
            <a href="/info" class="btn">ℹ️ Server Info</a>
        </div>

        <div style="margin-top: 2rem; opacity: 0.8;">
            <h3>📋 Prossimi passi:</h3>
            <p>1. Carica la tua app Flask in <code>/home/flaskapp/app/</code></p>
            <p>2. Configura Nginx per il tuo dominio</p>
            <p>3. Ottieni certificato SSL con Certbot</p>
            <p>4. Deploy in produzione con Gunicorn</p>
        </div>
    </div>
</body>
</html>
EOF

    log "✅ App Flask di test creata"
}

# 11. CONFIGURAZIONE NGINX BASE
configure_nginx() {
    log "🌐 Configurazione Nginx base..."

    # Backup configurazione default
    cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.backup

    # Crea configurazione base per Flask
    tee /etc/nginx/sites-available/flask-app > /dev/null << 'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /home/flaskapp/app/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
EOF

    # Disabilita default, abilita flask-app
    rm -f /etc/nginx/sites-enabled/default
    ln -sf /etc/nginx/sites-available/flask-app /etc/nginx/sites-enabled/

    # Test configurazione
    nginx -t

    # Riavvia Nginx
    systemctl reload nginx

    log "✅ Nginx configurato per Flask"
}

# 12. CREAZIONE SCRIPT DI GESTIONE
create_management_scripts() {
    log "📝 Creazione script di gestione..."

    # Script per avviare l'app
    tee /home/flaskapp/start_app.sh > /dev/null << 'EOF'
#!/bin/bash
cd /home/flaskapp/app
source venv/bin/activate
export FLASK_ENV=production
gunicorn --bind 127.0.0.1:5000 --workers 3 app:app
EOF

    # Script per sviluppo
    tee /home/flaskapp/dev_app.sh > /dev/null << 'EOF'
#!/bin/bash
cd /home/flaskapp/app
source venv/bin/activate
export FLASK_ENV=development
python app.py
EOF

    # Script per installare requirements
    tee /home/flaskapp/install_requirements.sh > /dev/null << 'EOF'
#!/bin/bash
cd /home/flaskapp/app
source venv/bin/activate
pip install -r requirements.txt
EOF

    # Rendi eseguibili
    chmod +x /home/flaskapp/*.sh
    chown flaskapp:flaskapp /home/flaskapp/*.sh

    log "✅ Script di gestione creati"
}

# 13. TEST FINALE
test_installation() {
    log "🧪 Test installazione..."

    # Test Python
    python3 --version
    pip3 --version

    # Test Flask environment
    sudo -u flaskapp bash -c "cd /home/flaskapp/app && source venv/bin/activate && python -c 'import flask; print(f\"Flask {flask.__version__} OK\")"

    # Test Nginx
    systemctl is-active nginx

    # Test servizi
    systemctl is-active postgresql 2>/dev/null && echo "PostgreSQL: OK" || echo "PostgreSQL: Not installed"
    systemctl is-active redis-server 2>/dev/null && echo "Redis: OK" || echo "Redis: Not installed"

    log "✅ Test completati"
}

# AVVIO APP DI TEST
start_test_app() {
    log "🚀 Avvio app di test..."

    # Avvia Flask in background
    sudo -u flaskapp bash -c "cd /home/flaskapp/app && source venv/bin/activate && nohup python app.py > flask.log 2>&1 &"

    sleep 3

    # Verifica che sia attiva
    if curl -s http://localhost:5000/health > /dev/null; then
        log "✅ App Flask attiva su porta 5000"
    else
        warning "⚠️ App Flask potrebbe non essere attiva"
    fi
}

# MOSTRA RIEPILOGO
show_summary() {
    echo ""
    echo "🎉 SETUP UBUNTU + FLASK COMPLETATO!"
    echo ""
    echo "📋 Software installato:"
    echo "   ✅ Ubuntu $(lsb_release -rs) aggiornato"
    echo "   ✅ Python $(python3 --version | cut -d' ' -f2)"
    echo "   ✅ Flask + dipendenze"
    echo "   ✅ Nginx web server"
    echo "   ✅ PostgreSQL database (se scelto)"
    echo "   ✅ Redis cache (se scelto)"
    echo "   ✅ Certbot per SSL"
    echo "   ✅ UFW firewall"
    echo ""
    echo "📁 Directory app: /home/flaskapp/app/"
    echo "👤 Utente app: flaskapp"
    echo ""
    echo "🔗 Test il server:"
    SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "TUO_IP")
    echo "   http://$SERVER_IP"
    echo "   http://$SERVER_IP/health"
    echo "   http://$SERVER_IP/info"
    echo ""
    echo "📝 Script utili:"
    echo "   /home/flaskapp/start_app.sh        # Avvia con Gunicorn"
    echo "   /home/flaskapp/dev_app.sh          # Modalità sviluppo"
    echo "   /home/flaskapp/install_requirements.sh  # Installa dipendenze"
    echo ""
    echo "🔄 Per sviluppare:"
    echo "   sudo su flaskapp"
    echo "   cd ~/app"
    echo "   source venv/bin/activate"
    echo "   # Sviluppa la tua app qui"
    echo ""
    echo "🚀 Per produzione:"
    echo "   1. Carica la tua app"
    echo "   2. Configura dominio su Nginx"
    echo "   3. Ottieni SSL: certbot --nginx -d tuodominio.com"
    echo "   4. Usa Gunicorn: /home/flaskapp/start_app.sh"
    echo ""
}

# MAIN EXECUTION
main() {
    echo "🚀 Setup Ubuntu + Flask Server"
    echo "💾 RAM: 2GB | 💽 SSD: 50GB"
    echo ""

    # Controlli preliminari
    if [ "$EUID" -ne 0 ]; then
        error "Esegui come root: sudo ./ubuntu_flask_setup.sh"
    fi

    check_ubuntu

    # Esecuzione step by step
    update_system
    install_python
    install_nginx
    setup_firewall
    install_nodejs
    install_databases
    create_app_user
    install_certbot
    create_flask_environment
    create_test_app
    configure_nginx
    create_management_scripts
    test_installation
    start_test_app
    show_summary

    log "🎉 Setup completato!"
}

# Esecuzione
main "$@"