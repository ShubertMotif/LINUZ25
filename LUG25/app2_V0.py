from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import json
import os
import hashlib
import uuid
import time
import threading
import queue
from datetime import datetime
from decimal import Decimal
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user

app = Flask(__name__)
app.secret_key = 'supersegreto'

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///adelchi_complete.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'


# =============================================================================
# DATABASE MODELS
# =============================================================================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    wallet_address = db.Column(db.String(200), unique=True, nullable=True)
    balance = db.Column(db.Float, default=0.0)
    total_earned = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tx_hash = db.Column(db.String(64), unique=True, nullable=False)
    from_wallet = db.Column(db.String(200), nullable=True)
    to_wallet = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    tx_type = db.Column(db.String(50), nullable=False)  # 'refresh', 'mining', 'transfer', 'login', 'registration'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    block_height = db.Column(db.Integer, nullable=True)
    confirmed = db.Column(db.Boolean, default=True)


class MiningSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    miner_name = db.Column(db.String(100), nullable=False)
    gpu_model = db.Column(db.String(50), nullable=False)
    hashrate = db.Column(db.Float, default=0.0)
    shares_found = db.Column(db.Integer, default=0)
    tokens_mined = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)


class Block(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    block_height = db.Column(db.Integer, unique=True, nullable=False)
    block_hash = db.Column(db.String(64), unique=True, nullable=False)
    previous_hash = db.Column(db.String(64), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    transactions_count = db.Column(db.Integer, default=0)
    mined_by = db.Column(db.String(200), nullable=True)


# =============================================================================
# BLOCKCHAIN SYSTEM
# =============================================================================

class RTX3060MiningPool:
    """Simulatore mining pool RTX 3060 con websocket (per ora disattivato)"""

    def __init__(self):
        self.is_active = False  # Mining pool spento per ora
        self.connected_gpus = []
        self.total_hashrate = 0.0
        self.processing_queue = queue.Queue()
        self.websocket_enabled = False  # Flag per connessione websocket

    def connect_gpu(self, gpu_id, hashrate):
        """Connette una GPU al pool"""
        if self.is_active:
            self.connected_gpus.append({
                'id': gpu_id,
                'hashrate': hashrate,
                'status': 'mining',
                'connected_at': datetime.now()
            })
            self.calculate_total_hashrate()

    def calculate_total_hashrate(self):
        """Calcola hashrate totale del pool"""
        self.total_hashrate = sum(gpu['hashrate'] for gpu in self.connected_gpus)

    def start_mining(self):
        """Avvia il mining pool (per ora simulato)"""
        self.is_active = True
        print("RTX3060 Mining Pool: ATTIVATO (modalità simulazione)")

    def stop_mining(self):
        """Ferma il mining pool"""
        self.is_active = False
        print("RTX3060 Mining Pool: DISATTIVATO")


class BlockchainSystem:
    """Sistema blockchain ADG completo"""

    def __init__(self):
        self.current_block_height = 1337
        self.total_supply = 12450
        self.mining_reward = 50.0  # ADG per blocco minato
        self.refresh_reward = 0.5  # ADG per visita sito
        self.login_reward = 1.0  # ADG per login
        self.registration_reward = 5.0  # ADG per registrazione
        self.mining_pool = RTX3060MiningPool()

    def generate_wallet_address(self, user_id):
        """Genera indirizzo wallet univoco ADG"""
        data = f"ADG{user_id}{int(time.time())}{user_id}"
        hash_obj = hashlib.sha256(data.encode())
        return f"ADG{hash_obj.hexdigest()[:32].upper()}"

    def create_transaction_hash(self, from_wallet, to_wallet, amount, tx_type):
        """Crea hash transazione"""
        tx_data = f"{from_wallet}{to_wallet}{amount}{tx_type}{time.time()}"
        return hashlib.sha256(tx_data.encode()).hexdigest()

    def create_transaction(self, from_wallet, to_wallet, amount, tx_type):
        """Crea e salva una transazione"""
        tx_hash = self.create_transaction_hash(from_wallet, to_wallet, amount, tx_type)

        transaction = Transaction(
            tx_hash=tx_hash,
            from_wallet=from_wallet,
            to_wallet=to_wallet,
            amount=amount,
            tx_type=tx_type,
            block_height=self.current_block_height,
            confirmed=True
        )

        db.session.add(transaction)
        return transaction

    def reward_user(self, user, amount, source='activity'):
        """Ricompensa utente con token ADG"""
        if not user.wallet_address:
            user.wallet_address = self.generate_wallet_address(user.id)

        # Aggiorna balance utente
        user.balance += amount
        user.total_earned += amount

        # Crea transazione
        transaction = self.create_transaction(
            from_wallet='SYSTEM_REWARD',
            to_wallet=user.wallet_address,
            amount=amount,
            tx_type=source
        )

        db.session.commit()
        print(f"ADG Reward: {user.username} riceve {amount} ADG per {source}")
        return transaction

    def mine_block(self, miner_address):
        """Mina un nuovo blocco (simulato se pool non attivo)"""
        if self.mining_pool.is_active:
            # Mining reale con pool RTX3060
            reward = self.mining_reward
            print(f"Blocco minato da pool RTX3060: {reward} ADG")
        else:
            # Mining simulato
            reward = self.mining_reward * 0.1  # Reward ridotto per simulazione
            print(f"Blocco simulato: {reward} ADG")

        self.current_block_height += 1
        return reward

    def get_mining_stats(self):
        """Statistiche mining"""
        return {
            'pool_active': self.mining_pool.is_active,
            'connected_gpus': len(self.mining_pool.connected_gpus),
            'total_hashrate': self.mining_pool.total_hashrate,
            'current_block': self.current_block_height,
            'websocket_enabled': self.mining_pool.websocket_enabled
        }


# Inizializza sistema blockchain
blockchain = BlockchainSystem()

# =============================================================================
# VISIT COUNTER SYSTEM
# =============================================================================

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


# =============================================================================
# MAIN ROUTES
# =============================================================================

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

    # Ricompensa utente loggato per visita con ADG
    if current_user.is_authenticated:
        blockchain.reward_user(current_user, blockchain.refresh_reward, 'refresh')

    return render_template('index.html', visit_count=visits_data['count'], current_user=current_user)


@app.route('/stats')
@login_required
def stats():
    visits_data = load_visits()
    return render_template('stats.html',
                           visit_count=visits_data['count'],
                           recent_visitors=visits_data['visitors'][-10:],
                           current_user=current_user)


# =============================================================================
# AUTHENTICATION ROUTES
# =============================================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash("Username già registrato.")
            return redirect(url_for('register'))

        # Crea nuovo utente con wallet
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.flush()  # Per ottenere l'ID

        # Genera wallet address
        new_user.wallet_address = blockchain.generate_wallet_address(new_user.id)

        # Bonus registrazione: 5 ADG
        blockchain.reward_user(new_user, blockchain.registration_reward, 'registration')

        flash(f"Registrazione completata! Ricevuti {blockchain.registration_reward} ADG di benvenuto!")
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
            # Ricompensa login giornaliero con ADG
            blockchain.reward_user(user, blockchain.login_reward, 'login')
            flash(f"Login effettuato! Ricevuto {blockchain.login_reward} ADG!")
            return redirect(url_for('index'))
        else:
            flash("Credenziali errate.")

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


# =============================================================================
# BLOCKCHAIN ROUTES
# =============================================================================

@app.route('/wallet')
@login_required
def wallet():
    """Dashboard wallet personale ADG"""
    # Assicura che l'utente abbia un wallet
    if not current_user.wallet_address:
        current_user.wallet_address = blockchain.generate_wallet_address(current_user.id)
        db.session.commit()

    # Ottieni transazioni dell'utente
    transactions = Transaction.query.filter_by(to_wallet=current_user.wallet_address) \
        .order_by(Transaction.timestamp.desc()) \
        .limit(20).all()

    # Dati wallet
    wallet_data = {
        'balance': current_user.balance,
        'wallet_address': current_user.wallet_address,
        'created_at': current_user.created_at
    }

    return render_template('wallet.html',
                           wallet=wallet_data,
                           transactions=transactions,
                           current_user=current_user)


@app.route('/mining')
@login_required
def mining():
    """Dashboard mining ADG"""
    # Ottieni miners dell'utente
    user_miners = MiningSession.query.filter_by(user_id=current_user.id).all()

    # Statistiche mining
    mining_stats = blockchain.get_mining_stats()

    return render_template('mining.html',
                           miners=user_miners,
                           mining_stats=mining_stats,
                           current_user=current_user)


@app.route('/mining/register', methods=['POST'])
@login_required
def register_miner():
    """Registra un nuovo miner RTX3060"""
    try:
        data = request.get_json() or request.form
        miner_name = data.get('miner_name') or data.get('minerName')
        gpu_model = data.get('gpu_model') or data.get('gpuModel')
        wallet_address = data.get('wallet_address') or data.get('walletAddress')

        # Verifica wallet
        if wallet_address and wallet_address != current_user.wallet_address:
            return jsonify({'success': False, 'message': 'Wallet address non valido'})

        if not current_user.wallet_address:
            current_user.wallet_address = blockchain.generate_wallet_address(current_user.id)
            db.session.commit()

        # Crea sessione mining
        mining_session = MiningSession(
            user_id=current_user.id,
            miner_name=miner_name,
            gpu_model=gpu_model,
            hashrate=_get_gpu_hashrate(gpu_model),
            is_active=False  # Non attivo finché pool non è avviato
        )

        db.session.add(mining_session)
        db.session.commit()

        # Ricompensa setup miner
        blockchain.reward_user(current_user, 2.0, 'mining_setup')

        return jsonify({'success': True, 'message': 'Miner registrato! +2 ADG bonus'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# =============================================================================
# ADMIN/API ROUTES
# =============================================================================

@app.route('/admin/toggle-mining', methods=['POST'])
@login_required
def toggle_mining():
    """Toggle sistema mining RTX3060 (admin only)"""
    # Per ora tutti possono attivare per test
    if blockchain.mining_pool.is_active:
        blockchain.mining_pool.stop_mining()
    else:
        blockchain.mining_pool.start_mining()

    return jsonify({
        'success': True,
        'mining_enabled': blockchain.mining_pool.is_active,
        'message': 'Mining pool ' + ('attivato' if blockchain.mining_pool.is_active else 'disattivato')
    })


@app.route('/api/balance/<username>')
def get_user_balance(username):
    """API bilancio utente"""
    user = User.query.filter_by(username=username).first()
    if user:
        return jsonify({
            'balance': user.balance,
            'total_earned': user.total_earned,
            'wallet_address': user.wallet_address
        })
    return jsonify({'error': 'User not found'}), 404


@app.route('/api/stats/blockchain')
def blockchain_stats():
    """Statistiche blockchain ADG"""
    total_users = User.query.count()
    total_transactions = Transaction.query.count()
    total_supply_distributed = db.session.query(db.func.sum(User.total_earned)).scalar() or 0
    active_miners = MiningSession.query.filter_by(is_active=True).count()

    return jsonify({
        'total_users': total_users,
        'total_transactions': total_transactions,
        'total_supply_distributed': round(total_supply_distributed, 2),
        'current_block_height': blockchain.current_block_height,
        'mining_pool_active': blockchain.mining_pool.is_active,
        'active_miners': active_miners,
        'total_hashrate': blockchain.mining_pool.total_hashrate
    })


@app.route('/api/mining/simulate-block')
@login_required
def simulate_mining():
    """Simula mining di un blocco (per testing)"""
    if current_user.wallet_address:
        reward = blockchain.mine_block(current_user.wallet_address)
        blockchain.reward_user(current_user, reward, 'mining')
        return jsonify({
            'success': True,
            'reward': reward,
            'new_balance': current_user.balance,
            'block_height': blockchain.current_block_height
        })
    return jsonify({'success': False, 'message': 'Wallet non trovato'})


# =============================================================================
# SERVICE ROUTES
# =============================================================================

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


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_gpu_hashrate(gpu_model):
    """Hashrate teorico per modello GPU (MH/s)"""
    hashrates = {
        'rtx4090': 120.0,
        'rtx4080': 95.0,
        'rtx4070': 75.0,
        'rtx3090': 85.0,
        'rtx3080': 70.0,
        'rtx3070': 55.0,
        'rtx3060': 45.0,  # La nostra GPU target
        'rx7900xt': 80.0,
        'rx6800xt': 65.0
    }
    return hashrates.get(gpu_model.lower(), 30.0)


# =============================================================================
# INITIALIZATION
# =============================================================================

def init_db():
    """Inizializza database se necessario"""
    try:
        db.create_all()
        print("ADG Blockchain System: Database inizializzato")
        print(f"Mining Pool RTX3060: {'ATTIVO' if blockchain.mining_pool.is_active else 'DISATTIVO'}")
        return True
    except Exception as e:
        print(f"Errore inizializzazione database: {e}")
        return False


# Inizializza database all'avvio dell'app
with app.app_context():
    init_db()

# =============================================================================
# WSGI APPLICATION OBJECT
# =============================================================================

# Per Gunicorn, l'oggetto application è l'app Flask
application = app

# =============================================================================
# WEBSOCKET INTEGRATION (PLACEHOLDER)
# =============================================================================

"""
Per integrare websocket con pool RTX3060 reale:

from flask_socketio import SocketIO, emit

socketio = SocketIO(app, cors_allowed_origins="*")

@socketio.on('gpu_connect')
def handle_gpu_connection(data):
    gpu_id = data.get('gpu_id')
    hashrate = data.get('hashrate', 45.0)  # RTX3060 default
    blockchain.mining_pool.connect_gpu(gpu_id, hashrate)
    emit('gpu_connected', {'status': 'connected', 'pool_hashrate': blockchain.mining_pool.total_hashrate})

@socketio.on('submit_share')
def handle_mining_share(data):
    if blockchain.mining_pool.is_active:
        # Processa share di mining
        user_id = data.get('user_id')
        nonce = data.get('nonce')
        # Logic per validare e ricompensare share
        pass
"""

# =============================================================================
# MAIN (per sviluppo locale)
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("ADELCHI BLOCKCHAIN SYSTEM - DEVELOPMENT MODE")
    print("=" * 60)
    print(f"Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"Mining Pool RTX3060: {'ATTIVO' if blockchain.mining_pool.is_active else 'DISATTIVATO'}")
    print(f"Websocket Ready: {blockchain.mining_pool.websocket_enabled}")
    print(f"Current Block Height: {blockchain.current_block_height}")
    print("Nota: Per produzione utilizzare Gunicorn")
    print("=" * 60)

    app.run(debug=True, host='0.0.0.0', port=5000) 