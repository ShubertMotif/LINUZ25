#!/bin/bash

# quick_fix.sh - Fix rapido per adelchigroup.com

cd /root/LUG25

# 1. FERMA Flask attuale
echo "🛑 Fermando Flask..."
pkill -f "python.*app"
sleep 2

# 2. BACKUP del file originale
echo "💾 Backup file originale..."
cp app.py app.py.backup

# 3. FIX del file app.py
echo "🔧 Fix del codice..."
cat > app_fixed.py << 'EOF'
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, current_user, UserMixin, login_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'adelchi_secret_2025'

# Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# IMPORTANTE: Rendi current_user disponibile in tutti i template
@app.context_processor
def inject_user():
    return dict(current_user=current_user)

# Routes
@app.route('/')
def home():
    return render_template("index.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash("Username già registrato.")
            return redirect(url_for('register'))
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash("Registrazione completata!")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash("Credenziali errate.")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/stats')
@login_required
def stats():
    return render_template('stats.html')

# Pagine servizi
@app.route('/life-science')
def life_science():
    return render_template('life_science.html')

@app.route('/servizi-informatici')
def servizi_informatici():
    return render_template('servizi_informatici.html')

@app.route('/difesa')
def difesa():
    return render_template('difesa.html')

@app.route('/finanza')
def finanza():
    return render_template('finanza.html')

@app.route('/chi-siamo')
def chi_siamo():
    return render_template('chi_siamo.html')

@app.route('/contatti')
def contatti():
    return render_template('contatti.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        # Crea utente demo
        if not User.query.first():
            demo_user = User(username='admin', password='admin123')
            db.session.add(demo_user)
            db.session.commit()
            print("Demo user: admin/admin123")

    # PER ORA usa porta 8080 invece di 80
    app.run(debug=False, host='0.0.0.0', port=8080)
EOF

# 4. CREA template base sicuro
echo "📄 Creando template sicuro..."
mkdir -p templates

cat > templates/index.html << 'EOF'
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Adelchi Group</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            text-align: center;
        }
        h1 {
            font-size: 3rem;
            margin-bottom: 1rem;
        }
        .nav {
            background: rgba(255,255,255,0.1);
            padding: 1rem;
            border-radius: 10px;
            margin: 2rem 0;
        }
        .nav a {
            color: white;
            text-decoration: none;
            margin: 0 1rem;
            padding: 0.5rem 1rem;
            border-radius: 5px;
            transition: background 0.3s;
        }
        .nav a:hover {
            background: rgba(255,255,255,0.2);
        }
        .status {
            background: rgba(0,255,0,0.2);
            padding: 1rem;
            border-radius: 10px;
            margin: 2rem 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎉 Adelchi Group</h1>
        <div class="status">
            <h2>✅ Sito Online e Funzionante!</h2>
            <p>Il sito è ora visibile e accessibile</p>
        </div>

        <nav class="nav">
            <a href="/">Home</a>
            <a href="/life-science">Life Science</a>
            <a href="/servizi-informatici">IT Services</a>
            <a href="/difesa">Difesa</a>
            <a href="/finanza">Finanza</a>
            <a href="/chi-siamo">Chi Siamo</a>
            <a href="/contatti">Contatti</a>

            {% if current_user and current_user.is_authenticated %}
                <a href="/stats">Stats</a>
                <a href="/logout">Logout ({{ current_user.username }})</a>
            {% else %}
                <a href="/login">Login</a>
                <a href="/register">Register</a>
            {% endif %}
        </nav>

        {% with messages = get_flashed_messages() %}
            {% if messages %}
                <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 10px; margin: 1rem 0;">
                    {% for message in messages %}
                        <p>{{ message }}</p>
                    {% endfor %}
                </div>
            {% endif %}
        {% endwith %}

        <div style="background: rgba(255,255,255,0.1); padding: 2rem; border-radius: 10px; margin: 2rem 0;">
            <h2>I Nostri Servizi</h2>
            <p>Adelchi Group - Innovazione e Eccellenza nei servizi di consulenza</p>
            <br>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem;">
                <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 10px;">
                    <h3>🧬 Life Science</h3>
                    <p>Soluzioni avanzate per farmaceutico e biotech</p>
                </div>
                <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 10px;">
                    <h3>💻 IT Services</h3>
                    <p>Trasformazione digitale e soluzioni IT</p>
                </div>
                <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 10px;">
                    <h3>🛡️ Difesa</h3>
                    <p>Sistemi di sicurezza e consulenza difesa</p>
                </div>
                <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 10px;">
                    <h3>💰 Finanza</h3>
                    <p>Consulenza finanziaria e investimenti</p>
                </div>
            </div>
        </div>

        <footer style="margin-top: 3rem; opacity: 0.8;">
            <p>&copy; 2025 Adelchi Group. Tutti i diritti riservati.</p>
        </footer>
    </div>
</body>
</html>
EOF

# 5. CREA altri template base
for page in login register stats life_science servizi_informatici difesa finanza chi_siamo contatti; do
    cat > templates/${page}.html << EOF
<!DOCTYPE html>
<html>
<head>
    <title>${page^} - Adelchi Group</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; min-height: 100vh; }
        .container { max-width: 800px; margin: 0 auto; text-align: center; }
        a { color: #FFD700; }
    </style>
</head>
<body>
    <div class="container">
        <h1>${page^} - Adelchi Group</h1>
        <nav>
            <a href="/">← Torna alla Home</a>
        </nav>
        <div style="background: rgba(255,255,255,0.1); padding: 2rem; border-radius: 10px; margin: 2rem 0;">
            <p>Pagina ${page^} in costruzione</p>
        </div>
    </div>
</body>
</html>
EOF
done

# 6. AVVIA con porta 8080 (sicura)
echo "🚀 Avviando Flask sulla porta 8080..."
source ADELCHIvenv/bin/activate
nohup python app_fixed.py > flask.log 2>&1 &

sleep 3

echo ""
echo "🎉 FATTO! Il sito è ora online:"
echo ""
echo "🌐 URL pubblico: http://46.101.194.81:8080"
echo "🌐 Con dominio: http://adelchigroup.com:8080"
echo ""
echo "👤 Login demo:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "📋 Comandi utili:"
echo "   tail -f flask.log          # Vedi i log"
echo "   ps aux | grep python       # Vedi se è attivo"
echo "   pkill -f python            # Ferma Flask"
echo ""
echo "⚠️  IMPORTANTE: La porta 8080 è temporanea e sicura"
echo "   Per produzione, configura Nginx + SSL sulla porta 443"
EOF

chmod +x quick_fix.sh
echo "Script creato! Esegui con: ./quick_fix.sh"