from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import json
import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from functools import wraps

app = Flask(__name__)
app.secret_key = 'supersegreto'

# Database configuration - esteso per supportare il gestionale
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///adelchi_group.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'


# Models estesi per il gestionale
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150))
    role = db.Column(db.String(50), default='user')  # admin, ecommerce, cosmetici, import_export, web_dev
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price_amazon = db.Column(db.Float, default=0.0)
    price_shopify = db.Column(db.Float, default=0.0)
    stock_amazon = db.Column(db.Integer, default=0)
    stock_shopify = db.Column(db.Integer, default=0)
    sku = db.Column(db.String(100), unique=True)
    category = db.Column(db.String(100))  # cosmetici, elettronica, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(100), nullable=False)
    platform = db.Column(db.String(50))  # amazon, shopify
    customer_name = db.Column(db.String(200))
    customer_email = db.Column(db.String(200))
    total_amount = db.Column(db.Float)
    status = db.Column(db.String(50))  # processing, shipped, delivered, cancelled
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class APISettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50))  # amazon, shopify
    api_key = db.Column(db.String(500))
    api_secret = db.Column(db.String(500))
    store_url = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


# Decorators per gestione ruoli
def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if current_user.role not in roles and current_user.role != 'admin':
                flash('Non hai i permessi per accedere a questa sezione.')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Accesso riservato agli amministratori.')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)

    return decorated_function


# Contatore visite (funzionalità esistente)
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


# Routes esistenti (mantenute identiche)
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
        email = request.form.get('email', '')

        if User.query.filter_by(username=username).first():
            flash("Username già registrato.")
            return redirect(url_for('register'))

        new_user = User(username=username, password=password, email=email)
        db.session.add(new_user)
        db.session.commit()
        flash("Registrazione completata! In attesa di approvazione amministratore.")
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user and user.is_active:
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash("Credenziali errate o account non attivato.")
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


# NUOVA ROUTE: Dashboard principale per utenti loggati
@app.route('/dashboard')
@login_required
def dashboard():
    user_stats = {}

    if current_user.role in ['admin', 'ecommerce']:
        # Stats e-commerce
        total_products = Product.query.count()
        total_orders = Order.query.count()
        today_orders = Order.query.filter(
            Order.created_at >= datetime.now().replace(hour=0, minute=0, second=0)
        ).count()
        recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()

        user_stats['ecommerce'] = {
            'products': total_products,
            'orders': total_orders,
            'today_orders': today_orders,
            'recent_orders': recent_orders
        }

    return render_template('dashboard.html', current_user=current_user, stats=user_stats)


# NUOVE ROUTES: Admin Panel
@app.route('/admin')
@admin_required
def admin_panel():
    users = User.query.all()
    return render_template('admin.html', current_user=current_user, users=users)


@app.route('/admin/user/update', methods=['POST'])
@admin_required
def update_user_role():
    user_id = request.form.get('user_id')
    new_role = request.form.get('role')
    is_active = request.form.get('is_active') == 'on'

    user = User.query.get(user_id)
    if user:
        user.role = new_role
        user.is_active = is_active
        db.session.commit()
        flash(f"Ruolo di {user.username} aggiornato a {new_role}")

    return redirect(url_for('admin_panel'))


# NUOVE ROUTES: E-commerce
@app.route('/ecommerce')
@role_required(['ecommerce'])
def ecommerce_dashboard():
    # Stats generali
    total_products = Product.query.count()
    total_orders = Order.query.count()
    today_orders = Order.query.filter(
        Order.created_at >= datetime.now().replace(hour=0, minute=0, second=0)
    ).count()

    # Ordini recenti
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()

    # Prodotti con stock basso
    low_stock = Product.query.filter(
        (Product.stock_amazon < 20) | (Product.stock_shopify < 20)
    ).all()

    return render_template('ecommerce/dashboard.html',
                           current_user=current_user,
                           total_products=total_products,
                           total_orders=total_orders,
                           today_orders=today_orders,
                           recent_orders=recent_orders,
                           low_stock=low_stock)


@app.route('/ecommerce/products')
@role_required(['ecommerce'])
def ecommerce_products():
    products = Product.query.all()
    return render_template('ecommerce/products.html',
                           current_user=current_user,
                           products=products)


@app.route('/ecommerce/products/add', methods=['GET', 'POST'])
@role_required(['ecommerce'])
def add_product():
    if request.method == 'POST':
        product = Product(
            name=request.form['name'],
            description=request.form['description'],
            price_amazon=float(request.form.get('price_amazon', 0)),
            price_shopify=float(request.form.get('price_shopify', 0)),
            stock_amazon=int(request.form.get('stock_amazon', 0)),
            stock_shopify=int(request.form.get('stock_shopify', 0)),
            sku=request.form['sku'],
            category=request.form.get('category', ''),
            created_by=current_user.id
        )
        db.session.add(product)
        db.session.commit()
        flash('Prodotto aggiunto con successo!')
        return redirect(url_for('ecommerce_products'))

    return render_template('ecommerce/add_product.html', current_user=current_user)


@app.route('/ecommerce/orders')
@role_required(['ecommerce'])
def ecommerce_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('ecommerce/orders.html',
                           current_user=current_user,
                           orders=orders)


@app.route('/ecommerce/settings')
@role_required(['ecommerce'])
def ecommerce_settings():
    amazon_settings = APISettings.query.filter_by(platform='amazon').first()
    shopify_settings = APISettings.query.filter_by(platform='shopify').first()

    return render_template('ecommerce/settings.html',
                           current_user=current_user,
                           amazon_settings=amazon_settings,
                           shopify_settings=shopify_settings)


# NUOVE ROUTES: API per AJAX
@app.route('/api/sync_stock/<int:product_id>', methods=['POST'])
@role_required(['ecommerce'])
def sync_stock(product_id):
    product = Product.query.get(product_id)
    if product:
        # Qui andrà la logica vera per sincronizzare con Amazon/Shopify
        # Per ora simulo
        import random
        product.stock_amazon = random.randint(10, 100)
        product.stock_shopify = random.randint(10, 100)
        db.session.commit()

        return jsonify({
            'success': True,
            'stock_amazon': product.stock_amazon,
            'stock_shopify': product.stock_shopify
        })

    return jsonify({'success': False})


@app.route('/api/update_prices/<int:product_id>', methods=['POST'])
@role_required(['ecommerce'])
def update_prices(product_id):
    product = Product.query.get(product_id)
    if product:
        data = request.get_json()
        product.price_amazon = data.get('price_amazon', product.price_amazon)
        product.price_shopify = data.get('price_shopify', product.price_shopify)
        db.session.commit()

        return jsonify({'success': True})

    return jsonify({'success': False})


# Routes esistenti per i servizi (mantenute identiche)
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


@app.route('/chi-siamo')
def chi_siamo():
    return render_template('chi_siamo.html', current_user=current_user)


@app.route('/contatti')
def contatti():
    return render_template('contatti.html', current_user=current_user)


# Funzione per creare admin e dati demo
def create_admin_and_demo_data():
    # Crea admin
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', password='admin123', role='admin', email='admin@adelchigroup.com')
        db.session.add(admin)
        print("Admin user created: admin/admin123")

    # Crea utente e-commerce demo
    ecommerce_user = User.query.filter_by(username='ecommerce').first()
    if not ecommerce_user:
        ecommerce_user = User(username='ecommerce', password='ecommerce123', role='ecommerce',
                              email='ecommerce@adelchigroup.com')
        db.session.add(ecommerce_user)
        print("E-commerce user created: ecommerce/ecommerce123")

    db.session.commit()

    # Crea prodotti demo
    if Product.query.count() == 0:
        demo_products = [
            Product(
                name="Smartphone XYZ Pro",
                description="Smartphone di ultima generazione con fotocamera avanzata",
                price_amazon=299.99,
                price_shopify=319.99,
                stock_amazon=45,
                stock_shopify=23,
                sku="SPH-XYZ-001",
                category="elettronica",
                created_by=admin.id
            ),
            Product(
                name="Auricolari Wireless Premium",
                description="Auricolari bluetooth con cancellazione del rumore",
                price_amazon=89.99,
                price_shopify=94.99,
                stock_amazon=67,
                stock_shopify=34,
                sku="AUR-WLS-002",
                category="elettronica",
                created_by=admin.id
            ),
            Product(
                name="Powerbank Ultra",
                description="Powerbank 20000mAh con ricarica rapida",
                price_amazon=39.99,
                price_shopify=42.99,
                stock_amazon=12,
                stock_shopify=8,
                sku="PWB-ULT-003",
                category="elettronica",
                created_by=admin.id
            )
        ]

        for product in demo_products:
            db.session.add(product)

        print("Demo products created")

    # Crea ordini demo
    if Order.query.count() == 0:
        demo_orders = [
            Order(
                order_id="AMZ-001234",
                platform="amazon",
                customer_name="Mario Rossi",
                customer_email="mario.rossi@email.com",
                total_amount=299.99,
                status="processing",
                product_id=1,
                quantity=1
            ),
            Order(
                order_id="SPF-005678",
                platform="shopify",
                customer_name="Laura Bianchi",
                customer_email="laura.bianchi@email.com",
                total_amount=94.99,
                status="shipped",
                product_id=2,
                quantity=1
            ),
            Order(
                order_id="AMZ-001235",
                platform="amazon",
                customer_name="Giuseppe Verdi",
                customer_email="giuseppe.verdi@email.com",
                total_amount=42.99,
                status="delivered",
                product_id=3,
                quantity=1
            )
        ]

        for order in demo_orders:
            db.session.add(order)

        print("Demo orders created")

    db.session.commit()


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_admin_and_demo_data()
    app.run(debug=True, host='0.0.0.0', port=5000)