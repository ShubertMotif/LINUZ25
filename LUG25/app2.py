from flask import Flask, render_template, request, redirect, url_for, flash
import json
import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user

app = Flask(__name__)
app.secret_key = 'supersegreto'

# Database utenti
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

# Contatore visite
VISITS_FILE = 'visits.json'
if not os.path.exists('static'):
    os.makedirs('static')

def load_visits():
    if os.path.exists(VISITS_FILE):
        try:
            with open(VISITS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {'count': 0, 'visitors': []}
    return {'count': 0, 'visitors': []}

def save_visits(visits_data):
    with open(VISITS_FILE, 'w') as f:
        json.dump(visits_data, f, indent=2)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    visits_data = load_visits()
    visits_data['count'] += 1
    visitor_info = {
        'timestamp': datetime.now().isoformat(),
        'ip': request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown')),
        'user_agent': request.environ.get('HTTP_USER_AGENT', 'unknown'),
        'user': current_user.username if current_user.is_authenticated else 'Anonimo'
    }
    visits_data['visitors'].append(visitor_info)
    if len(visits_data['visitors']) > 100:
        visits_data['visitors'] = visits_data['visitors'][-100:]
    save_visits(visits_data)
    return render_template('index.html', visit_count=visits_data['count'], current_user=current_user)

@app.route('/stats')
@login_required
def stats():
    visits_data = load_visits()
    return render_template('stats.html',
                           visit_count=visits_data['count'],
                           recent_visitors=visits_data['visitors'][-10:],
                           current_user=current_user)

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
            return redirect(url_for('index'))
        else:
            flash("Credenziali errate.")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Nuove route per i servizi
@app.route('/life-science')
def life_science():
    return render_template('life_science.html', current_user=current_user)

@app.route('/servizi-informatici')
def servizi_informatici():
    return render_template('servizi_informatici.html', current_user=current_user)

@app.route('/difesa')
def difesa():
    return render_template('difesa.html', current_user=current_user)

@app.route('/finanza')
def finanza():
    return render_template('finanza.html', current_user=current_user)

# Nuove route per pagine statiche
@app.route('/chi-siamo')
def chi_siamo():
    return render_template('chi_siamo.html', current_user=current_user)

@app.route('/contatti')
def contatti():
    return render_template('contatti.html', current_user=current_user)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)


#host='0.0.0.0', port=80