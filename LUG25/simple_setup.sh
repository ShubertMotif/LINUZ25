#!/bin/bash

# simple_setup.sh - Far girare app2.py su porta 80 SUBITO

echo "🚀 Setup semplice per app2.py su porta 80"

# 1. FERMA TUTTO quello che usa porta 80
echo "🛑 Fermando servizi su porta 80..."
sudo systemctl stop nginx 2>/dev/null
sudo systemctl stop apache2 2>/dev/null
sudo pkill -f "python.*app" 2>/dev/null
sudo pkill -f ":80" 2>/dev/null

# Aspetta che si liberino le porte
sleep 3

# 2. VERIFICA che la porta 80 sia libera
if sudo netstat -tlnp | grep :80; then
    echo "❌ Porta 80 ancora occupata. Forzo la chiusura..."
    sudo fuser -k 80/tcp 2>/dev/null
    sleep 2
fi

# 3. VAI nella directory dell'app
cd /root/LUG25 || {
    echo "❌ Directory /root/LUG25 non trovata!"
    echo "Dove si trova app2.py? Specifica il path:"
    read -p "Path: " APP_PATH
    cd "$APP_PATH" || exit 1
}

echo "📍 Directory corrente: $(pwd)"
echo "📁 File presenti:"
ls -la

# 4. ATTIVA virtual environment se esiste
if [ -d "ADELCHIvenv" ]; then
    echo "🐍 Attivando virtual environment..."
    source ADELCHIvenv/bin/activate
elif [ -d "venv" ]; then
    echo "🐍 Attivando virtual environment..."
    source venv/bin/activate
else
    echo "⚠️ Nessun virtual environment trovato, uso Python sistema"
fi

# 5. VERIFICA che app2.py esista
if [ ! -f "app2.py" ]; then
    echo "❌ File app2.py non trovato!"
    echo "File Python presenti:"
    ls -la *.py 2>/dev/null
    echo ""
    read -p "Nome del file dell'app (es. app.py): " APP_FILE
    if [ ! -f "$APP_FILE" ]; then
        echo "❌ File $APP_FILE non trovato!"
        exit 1
    fi
    APP_FILE="app2.py"
else
    APP_FILE="app2.py"
fi

# 6. MODIFICA app2.py per porta 80
echo "🔧 Configurando $APP_FILE per porta 80..."

# Backup del file originale
cp "$APP_FILE" "${APP_FILE}.backup"

# Modifica la riga app.run per porta 80
sed -i "s/app\.run(.*/app.run(debug=False, host='0.0.0.0', port=80)/" "$APP_FILE"

# Se non trova app.run, aggiungila
if ! grep -q "app.run" "$APP_FILE"; then
    echo "" >> "$APP_FILE"
    echo "if __name__ == '__main__':" >> "$APP_FILE"
    echo "    app.run(debug=False, host='0.0.0.0', port=80)" >> "$APP_FILE"
fi

echo "✅ $APP_FILE configurato per porta 80"

# 7. INSTALLA dipendenze se mancano
echo "📦 Verificando dipendenze..."
python3 -c "import flask" 2>/dev/null || pip3 install flask
python3 -c "import flask_sqlalchemy" 2>/dev/null || pip3 install flask-sqlalchemy
python3 -c "import flask_login" 2>/dev/null || pip3 install flask-login

# 8. CREA un servizio systemd semplice
echo "⚙️ Creando servizio systemd..."

sudo tee /etc/systemd/system/app2.service > /dev/null << EOF
[Unit]
Description=App2 Flask Application
After=network.target

[Service]
Type=exec
User=root
Group=root
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/ADELCHIvenv/bin:$(pwd)/venv/bin:/usr/bin
ExecStart=/usr/bin/python3 $APP_FILE
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 9. AVVIA il servizio
echo "🚀 Avviando app2.py..."

sudo systemctl daemon-reload
sudo systemctl enable app2
sudo systemctl start app2

# 10. VERIFICA che sia attivo
sleep 3

if sudo systemctl is-active --quiet app2; then
    echo "✅ app2.py è attivo!"
else
    echo "❌ Problema con app2. Vediamo i log:"
    sudo journalctl -u app2 -n 10 --no-pager
fi

# 11. TEST connessione
echo "🔍 Test connessione..."

SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')

if curl -s --max-time 5 http://localhost/ > /dev/null; then
    echo "✅ App risponde su localhost"
else
    echo "❌ App non risponde su localhost"
fi

if curl -s --max-time 5 http://$SERVER_IP/ > /dev/null; then
    echo "✅ App risponde su IP pubblico"
else
    echo "❌ App non risponde su IP pubblico"
fi

# 12. CONFIGURA firewall
echo "🔥 Configurando firewall..."
sudo ufw allow 80/tcp 2>/dev/null
sudo ufw allow ssh 2>/dev/null

echo ""
echo "🎉 FATTO! app2.py gira su porta 80"
echo ""
echo "🌐 URL del sito:"
echo "   http://$SERVER_IP"
echo "   http://adelchigroup.com (se DNS configurato)"
echo ""
echo "🎛️ Comandi utili:"
echo "   sudo systemctl status app2        # Stato app"
echo "   sudo systemctl restart app2       # Riavvia app"
echo "   sudo systemctl stop app2          # Ferma app"
echo "   sudo journalctl -u app2 -f        # Log in tempo reale"
echo ""
echo "📁 File:"
echo "   App: $(pwd)/$APP_FILE"
echo "   Backup: $(pwd)/${APP_FILE}.backup"
echo ""

# Se c'è un errore, mostra i log
if ! sudo systemctl is-active --quiet app2; then
    echo "⚠️ ATTENZIONE: L'app potrebbe avere problemi."
    echo "Ultimi log:"
    sudo journalctl -u app2 -n 5 --no-pager
fi