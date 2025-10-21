from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
import json
import os
import hashlib
import uuid
import time
import threading
import queue
import jwt
from datetime import datetime, timedelta
from decimal import Decimal
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from functools import wraps

app = Flask(__name__)
app.secret_key = 'supersegreto'

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///adelchi_complete.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'zip',
                      'rar'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# JWT Configuration
JWT_SECRET = 'your-secret-key-here-change-in-production'
JWT_ALGORITHM = 'HS256'

# Create folders if they don't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists('static'):
    os.makedirs('static')

login_manager = LoginManager(app)
login_manager.login_view = 'login'


# =============================================================================
# DATABASE MODELS
# =============================================================================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), default='employee')  # 'manager' or 'employee'
    wallet_address = db.Column(db.String(200), unique=True, nullable=True)
    balance = db.Column(db.Float, default=0.0)
    total_earned = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def can_create_projects(self):
        """Solo i manager possono creare progetti"""
        return self.role == 'manager'

    def get_role_display(self):
        """Ritorna nome ruolo per UI"""
        return 'Manager' if self.role == 'manager' else 'Employee'


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


class UserFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)  # 'image', 'document', 'other'
    file_size = db.Column(db.Integer, nullable=False)  # in bytes
    file_path = db.Column(db.String(500), nullable=False)
    mime_type = db.Column(db.String(100), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_public = db.Column(db.Boolean, default=False)

    # Relationship
    user = db.relationship('User', backref=db.backref('files', lazy=True))


class UserNote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    note_type = db.Column(db.String(50), default='text')  # 'text', 'link', 'task', 'idea'
    priority = db.Column(db.String(20), default='normal')  # 'low', 'normal', 'high', 'urgent'
    tags = db.Column(db.String(500), nullable=True)  # comma-separated tags
    external_url = db.Column(db.String(1000), nullable=True)  # for link notes
    due_date = db.Column(db.DateTime, nullable=True)  # for task notes
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user = db.relationship('User', backref=db.backref('notes', lazy=True))


class NoteFile(db.Model):
    """Associazione tra note e file allegati"""
    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('user_note.id'), nullable=False)
    file_id = db.Column(db.Integer, db.ForeignKey('user_file.id'), nullable=False)
    attachment_type = db.Column(db.String(50), default='attachment')  # 'attachment', 'inline_image'

    # Relationships
    note = db.relationship('UserNote', backref=db.backref('attached_files', lazy=True))
    file = db.relationship('UserFile', backref=db.backref('note_attachments', lazy=True))


class FileShare(db.Model):
    """Condivisione file tra utenti"""
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('user_file.id'), nullable=False)
    shared_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    shared_with = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    permission = db.Column(db.String(20), default='view')  # 'view', 'edit', 'download'
    shared_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    file = db.relationship('UserFile', backref=db.backref('shares', lazy=True))
    sharer = db.relationship('User', foreign_keys=[shared_by], backref='shared_files')
    recipient = db.relationship('User', foreign_keys=[shared_with], backref='received_files')


class Project(db.Model):
    """Progetto aziendale con team members"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    owner = db.relationship('User', backref=db.backref('owned_projects', lazy=True))

    def get_member_count(self):
        """Conta membri del progetto"""
        return ProjectMember.query.filter_by(project_id=self.id).count()

    def get_file_count(self):
        """Conta file nel progetto"""
        return ProjectFile.query.filter_by(project_id=self.id).count()

    def get_note_count(self):
        """Conta note nel progetto"""
        return ProjectNote.query.filter_by(project_id=self.id).count()

    def get_members(self):
        """Ottieni tutti i membri"""
        return ProjectMember.query.filter_by(project_id=self.id).all()

    def get_user_role(self, user_id):
        """Ottieni ruolo di un utente nel progetto"""
        member = ProjectMember.query.filter_by(project_id=self.id, user_id=user_id).first()
        return member.role if member else None


class ProjectMember(db.Model):
    """Membri di un progetto con ruoli"""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'owner', 'collaborator', 'viewer'
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    project = db.relationship('Project', backref=db.backref('members', lazy=True))
    user = db.relationship('User', backref=db.backref('project_memberships', lazy=True))


class ProjectFile(db.Model):
    """Link tra progetti e file"""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    file_id = db.Column(db.Integer, db.ForeignKey('user_file.id'), nullable=False)
    added_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    project = db.relationship('Project', backref=db.backref('project_files', lazy=True))
    file = db.relationship('UserFile', backref=db.backref('in_projects', lazy=True))


class ProjectNote(db.Model):
    """Link tra progetti e note"""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    note_id = db.Column(db.Integer, db.ForeignKey('user_note.id'), nullable=False)
    added_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    project = db.relationship('Project', backref=db.backref('project_notes', lazy=True))
    note = db.relationship('UserNote', backref=db.backref('in_projects', lazy=True))


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
        # RICOMPENSE PER ATTIVITÀ UTENTE
        self.file_upload_reward = 0.3  # ADG per upload file
        self.note_creation_reward = 0.2  # ADG per creazione nota
        self.note_completion_reward = 0.5  # ADG per completamento task
        self.project_creation_reward = 2.0  # ADG per creazione progetto
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


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_type(filename):
    ext = filename.rsplit('.', 1)[1].lower()
    if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']:
        return 'image'
    elif ext in ['pdf', 'doc', 'docx', 'txt', 'rtf', 'xls', 'xlsx', 'ppt', 'pptx']:
        return 'document'
    else:
        return 'other'


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


# JWT Functions
def generate_token(user_id):
    """Genera JWT token"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=30)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token):
    """Verifica JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def token_required(f):
    """Decorator per routes che richiedono autenticazione"""

    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'success': False, 'message': 'Token mancante'}), 401

        if token.startswith('Bearer '):
            token = token[7:]

        user_id = verify_token(token)
        if not user_id:
            return jsonify({'success': False, 'message': 'Token invalido'}), 401

        # Ottieni utente
        current_user = User.query.get(user_id)
        if not current_user:
            return jsonify({'success': False, 'message': 'Utente non trovato'}), 401

        return f(current_user, *args, **kwargs)

    return decorated


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
# BLOCCO 2: ROUTES SISTEMA PROGETTI
# =============================================================================
# ISTRUZIONI:
# INCOLLA questo blocco DOPO @app.route('/logout') (dopo riga 456 circa)
# PRIMA della sezione # BLOCKCHAIN ROUTES
# =============================================================================

# =============================================================================
# PROJECT ROUTES
# =============================================================================

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard personale con progetti"""
    # Progetti di cui sono owner
    owned = Project.query.filter_by(owner_id=current_user.id).all()

    # Progetti dove sono collaborator
    collab_memberships = ProjectMember.query.filter_by(
        user_id=current_user.id,
        role='collaborator'
    ).all()
    collaborating = [m.project for m in collab_memberships]

    # Progetti dove sono viewer
    view_memberships = ProjectMember.query.filter_by(
        user_id=current_user.id,
        role='viewer'
    ).all()
    viewing = [m.project for m in view_memberships]

    # Raggruppa progetti
    projects = {
        'owned': owned,
        'collaborating': collaborating,
        'viewing': viewing,
        'total': len(owned) + len(collaborating) + len(viewing)
    }

    return render_template('dashboard.html',
                           projects=projects,
                           current_user=current_user)


@app.route('/projects')
@login_required
def projects_list():
    """Lista completa progetti accessibili"""
    # Progetti di cui sono owner
    owned = Project.query.filter_by(owner_id=current_user.id).all()

    # Progetti dove sono collaborator
    collab_memberships = ProjectMember.query.filter_by(
        user_id=current_user.id,
        role='collaborator'
    ).all()
    collaborating = [m.project for m in collab_memberships]

    # Progetti dove sono viewer
    view_memberships = ProjectMember.query.filter_by(
        user_id=current_user.id,
        role='viewer'
    ).all()
    viewing = [m.project for m in view_memberships]

    # Raggruppa progetti
    projects = {
        'owned': owned,
        'collaborating': collaborating,
        'viewing': viewing,
        'total': len(owned) + len(collaborating) + len(viewing)
    }

    return render_template('project_list.html',
                           projects=projects,
                           current_user=current_user)


@app.route('/create_project', methods=['GET', 'POST'])
@login_required
def create_project():
    """Crea nuovo progetto (solo manager)"""
    # Verifica permessi
    if not current_user.can_create_projects():
        flash('Solo i Manager possono creare progetti')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            name = request.form.get('name')
            description = request.form.get('description', '')

            if not name:
                flash('Nome progetto obbligatorio')
                return redirect(url_for('create_project'))

            # Crea progetto
            project = Project(
                name=name,
                description=description,
                owner_id=current_user.id
            )
            db.session.add(project)
            db.session.flush()  # Per ottenere l'ID

            # Aggiungi owner come membro
            owner_member = ProjectMember(
                project_id=project.id,
                user_id=current_user.id,
                role='owner'
            )
            db.session.add(owner_member)
            db.session.commit()

            # Ricompensa ADG per creazione progetto
            blockchain.reward_user(current_user, blockchain.project_creation_reward, 'project_creation')

            flash(f'Progetto "{name}" creato con successo! +{blockchain.project_creation_reward} ADG')
            return redirect(url_for('project_detail', project_id=project.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Errore: {str(e)}')
            return redirect(url_for('create_project'))

    # GET - mostra form
    return render_template('create_project.html', current_user=current_user)


@app.route('/project/<int:project_id>')
@login_required
def project_detail(project_id):
    """Dettaglio progetto"""
    project = Project.query.get_or_404(project_id)

    # Verifica accesso
    member = ProjectMember.query.filter_by(
        project_id=project_id,
        user_id=current_user.id
    ).first()

    if not member and project.owner_id != current_user.id:
        flash('Non hai accesso a questo progetto')
        return redirect(url_for('dashboard'))

    # Determina ruolo utente
    user_role = member.role if member else 'owner'

    # Ottieni membri, file e note del progetto
    members = project.get_members()
    project_files = ProjectFile.query.filter_by(project_id=project_id).all()
    project_notes = ProjectNote.query.filter_by(project_id=project_id).all()

    # Utenti disponibili da aggiungere (solo per owner)
    available_users = []
    if user_role == 'owner':
        member_ids = [m.user_id for m in members]
        available_users = User.query.filter(
            User.id != current_user.id,
            ~User.id.in_(member_ids)
        ).all()

    return render_template('project_detail.html',
                           project=project,
                           user_role=user_role,
                           members=members,
                           project_files=project_files,
                           project_notes=project_notes,
                           available_users=available_users,
                           current_user=current_user)


@app.route('/project/<int:project_id>/add_member', methods=['POST'])
@login_required
def add_project_member(project_id):
    """Aggiungi membro al progetto (solo owner)"""
    project = Project.query.get_or_404(project_id)

    # Verifica che sia owner
    if project.owner_id != current_user.id:
        return jsonify({'success': False, 'message': 'Solo il proprietario può aggiungere membri'}), 403

    try:
        data = request.get_json() or request.form
        user_id = data.get('user_id')
        role = data.get('role', 'viewer')  # Default: viewer

        if not user_id:
            return jsonify({'success': False, 'message': 'user_id mancante'}), 400

        # Verifica che l'utente esista
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'Utente non trovato'}), 404

        # Verifica che non sia già membro
        existing = ProjectMember.query.filter_by(
            project_id=project_id,
            user_id=user_id
        ).first()

        if existing:
            return jsonify({'success': False, 'message': 'Utente già nel progetto'}), 400

        # Aggiungi membro
        member = ProjectMember(
            project_id=project_id,
            user_id=user_id,
            role=role
        )
        db.session.add(member)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'{user.username} aggiunto come {role}'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/project/<int:project_id>/remove_member/<int:user_id>', methods=['POST'])
@login_required
def remove_project_member(project_id, user_id):
    """Rimuovi membro dal progetto (solo owner)"""
    project = Project.query.get_or_404(project_id)

    # Verifica che sia owner
    if project.owner_id != current_user.id:
        return jsonify({'success': False, 'message': 'Solo il proprietario può rimuovere membri'}), 403

    try:
        # Trova membro
        member = ProjectMember.query.filter_by(
            project_id=project_id,
            user_id=user_id
        ).first()

        if not member:
            return jsonify({'success': False, 'message': 'Membro non trovato'}), 404

        # Non permettere rimozione owner
        if member.role == 'owner':
            return jsonify({'success': False, 'message': 'Non puoi rimuovere il proprietario'}), 400

        # Rimuovi membro
        db.session.delete(member)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Membro rimosso dal progetto'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


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
# FILE MANAGEMENT ROUTES
# =============================================================================

@app.route('/files')
@login_required
def files_dashboard():
    """Dashboard file utente"""
    user_files = UserFile.query.filter_by(user_id=current_user.id) \
        .order_by(UserFile.uploaded_at.desc()).all()

    # Statistiche
    total_files = len(user_files)
    total_size = sum(f.file_size for f in user_files)

    # Raggruppa per tipo
    files_by_type = {}
    for file in user_files:
        if file.file_type not in files_by_type:
            files_by_type[file.file_type] = []
        files_by_type[file.file_type].append(file)

    return render_template('files_dashboard.html',
                           files=user_files,
                           files_by_type=files_by_type,
                           total_files=total_files,
                           total_size=total_size,
                           current_user=current_user)


@app.route('/upload_file', methods=['POST'])
@login_required
def upload_file():
    """Upload singolo file con ricompensa ADG"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'Nessun file selezionato'})

        file = request.files['file']

        if file.filename == '':
            return jsonify({'success': False, 'message': 'Nessun file selezionato'})

        if not allowed_file(file.filename):
            return jsonify({'success': False, 'message': 'Tipo file non consentito'})

        # Genera nome file sicuro
        original_filename = file.filename
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        safe_filename = f"{uuid.uuid4().hex}.{file_extension}"

        # Percorso completo
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)

        # Salva file
        file.save(file_path)

        # Ottieni informazioni file
        file_size = os.path.getsize(file_path)
        file_type = get_file_type(original_filename)

        # Salva nel database
        user_file = UserFile(
            user_id=current_user.id,
            filename=safe_filename,
            original_filename=original_filename,
            file_type=file_type,
            file_size=file_size,
            file_path=file_path,
            mime_type=file.mimetype
        )

        db.session.add(user_file)
        db.session.commit()

        # RICOMPENSA ADG PER UPLOAD FILE
        blockchain.reward_user(current_user, blockchain.file_upload_reward, 'file_upload')

        return jsonify({
            'success': True,
            'message': f'File caricato con successo! +{blockchain.file_upload_reward} ADG',
            'file_id': user_file.id,
            'filename': original_filename,
            'file_type': file_type,
            'file_size': file_size,
            'adg_earned': blockchain.file_upload_reward
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'Errore: {str(e)}'})


@app.route('/download_file/<int:file_id>')
@login_required
def download_file(file_id):
    """Download file"""
    file_record = UserFile.query.filter_by(id=file_id, user_id=current_user.id).first()

    if not file_record:
        flash('File non trovato')
        return redirect(url_for('files_dashboard'))

    try:
        return send_file(
            file_record.file_path,
            as_attachment=True,
            download_name=file_record.original_filename,
            mimetype=file_record.mime_type
        )
    except FileNotFoundError:
        flash('File fisico non trovato')
        return redirect(url_for('files_dashboard'))


@app.route('/delete_file/<int:file_id>', methods=['POST'])
@login_required
def delete_file(file_id):
    """Elimina file"""
    file_record = UserFile.query.filter_by(id=file_id, user_id=current_user.id).first()

    if not file_record:
        return jsonify({'success': False, 'message': 'File non trovato'})

    try:
        # Rimuovi file fisico
        if os.path.exists(file_record.file_path):
            os.remove(file_record.file_path)

        # Rimuovi dal database
        db.session.delete(file_record)
        db.session.commit()

        return jsonify({'success': True, 'message': 'File eliminato'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Errore: {str(e)}'})


# =============================================================================
# NOTES MANAGEMENT ROUTES
# =============================================================================

@app.route('/notes')
@login_required
def notes_dashboard():
    """Dashboard note utente"""
    # Filtri
    note_type = request.args.get('type', '')
    priority = request.args.get('priority', '')
    search = request.args.get('search', '')

    # Query base
    query = UserNote.query.filter_by(user_id=current_user.id)

    # Applica filtri
    if note_type:
        query = query.filter_by(note_type=note_type)
    if priority:
        query = query.filter_by(priority=priority)
    if search:
        query = query.filter(UserNote.title.contains(search) |
                             UserNote.content.contains(search))

    notes = query.order_by(UserNote.updated_at.desc()).all()

    # Statistiche
    total_notes = UserNote.query.filter_by(user_id=current_user.id).count()
    completed_tasks = UserNote.query.filter_by(
        user_id=current_user.id, note_type='task', completed=True
    ).count()
    pending_tasks = UserNote.query.filter_by(
        user_id=current_user.id, note_type='task', completed=False
    ).count()

    return render_template('notes_dashboard.html',
                           notes=notes,
                           total_notes=total_notes,
                           completed_tasks=completed_tasks,
                           pending_tasks=pending_tasks,
                           current_user=current_user)


@app.route('/create_note', methods=['GET', 'POST'])
@login_required
def create_note():
    """Crea nuova nota con ricompensa ADG"""
    if request.method == 'POST':
        try:
            data = request.get_json() or request.form

            note = UserNote(
                user_id=current_user.id,
                title=data.get('title'),
                content=data.get('content'),
                note_type=data.get('note_type', 'text'),
                priority=data.get('priority', 'normal'),
                tags=data.get('tags', ''),
                external_url=data.get('external_url')
            )

            # Se è un task con due date
            if data.get('due_date'):
                try:
                    note.due_date = datetime.strptime(data.get('due_date'), '%Y-%m-%d')
                except:
                    pass

            db.session.add(note)
            db.session.flush()  # Per ottenere l'ID

            # Allega file se presenti
            if 'attached_files' in data:
                file_ids = data.get('attached_files', '').split(',')
                for file_id in file_ids:
                    if file_id.strip():
                        note_file = NoteFile(note_id=note.id, file_id=int(file_id.strip()))
                        db.session.add(note_file)

            db.session.commit()

            # RICOMPENSA ADG PER CREAZIONE NOTA
            blockchain.reward_user(current_user, blockchain.note_creation_reward, 'note_creation')

            if request.is_json:
                return jsonify({
                    'success': True,
                    'note_id': note.id,
                    'message': f'Nota creata! +{blockchain.note_creation_reward} ADG',
                    'adg_earned': blockchain.note_creation_reward
                })
            else:
                flash(f'Nota creata con successo! +{blockchain.note_creation_reward} ADG')
                return redirect(url_for('notes_dashboard'))

        except Exception as e:
            if request.is_json:
                return jsonify({'success': False, 'message': f'Errore: {str(e)}'})
            else:
                flash(f'Errore: {str(e)}')
                return redirect(url_for('notes_dashboard'))

    # GET - mostra form
    user_files = UserFile.query.filter_by(user_id=current_user.id).all()
    return render_template('create_note.html', user_files=user_files, current_user=current_user)


@app.route('/edit_note/<int:note_id>', methods=['GET', 'POST'])
@login_required
def edit_note(note_id):
    """Modifica nota con ricompensa per completamento task"""
    note = UserNote.query.filter_by(id=note_id, user_id=current_user.id).first()

    if not note:
        flash('Nota non trovata')
        return redirect(url_for('notes_dashboard'))

    if request.method == 'POST':
        try:
            data = request.get_json() or request.form

            # Controlla se è un task che viene completato per la prima volta
            was_incomplete_task = (note.note_type == 'task' and not note.completed)

            note.title = data.get('title')
            note.content = data.get('content')
            note.note_type = data.get('note_type', note.note_type)
            note.priority = data.get('priority', note.priority)
            note.tags = data.get('tags', '')
            note.external_url = data.get('external_url')
            note.updated_at = datetime.utcnow()

            # Task completion
            task_completed_now = False
            if 'completed' in data:
                new_completed_status = bool(data.get('completed'))
                if was_incomplete_task and new_completed_status:
                    task_completed_now = True
                note.completed = new_completed_status

            db.session.commit()

            # RICOMPENSA ADG PER COMPLETAMENTO TASK
            if task_completed_now:
                blockchain.reward_user(current_user, blockchain.note_completion_reward, 'task_completion')

            success_message = 'Nota aggiornata'
            if task_completed_now:
                success_message += f'! +{blockchain.note_completion_reward} ADG per completamento task'

            if request.is_json:
                response_data = {
                    'success': True,
                    'message': success_message
                }
                if task_completed_now:
                    response_data['adg_earned'] = blockchain.note_completion_reward
                return jsonify(response_data)
            else:
                flash(success_message)
                return redirect(url_for('notes_dashboard'))

        except Exception as e:
            if request.is_json:
                return jsonify({'success': False, 'message': f'Errore: {str(e)}'})
            else:
                flash(f'Errore: {str(e)}')

    return render_template('edit_note.html', note=note, current_user=current_user)


@app.route('/delete_note/<int:note_id>', methods=['POST'])
@login_required
def delete_note(note_id):
    """Elimina nota"""
    note = UserNote.query.filter_by(id=note_id, user_id=current_user.id).first()

    if not note:
        return jsonify({'success': False, 'message': 'Nota non trovata'})

    try:
        # Rimuovi allegati
        NoteFile.query.filter_by(note_id=note.id).delete()

        # Rimuovi nota
        db.session.delete(note)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Nota eliminata'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Errore: {str(e)}'})


@app.route('/api/notes/search')
@login_required
def search_notes():
    """API ricerca note"""
    query = request.args.get('q', '')
    note_type = request.args.get('type', '')

    base_query = UserNote.query.filter_by(user_id=current_user.id)

    if query:
        base_query = base_query.filter(
            UserNote.title.contains(query) |
            UserNote.content.contains(query) |
            UserNote.tags.contains(query)
        )

    if note_type:
        base_query = base_query.filter_by(note_type=note_type)

    notes = base_query.order_by(UserNote.updated_at.desc()).limit(20).all()

    return jsonify({
        'notes': [{
            'id': note.id,
            'title': note.title,
            'content': note.content[:100],
            'type': note.note_type,
            'priority': note.priority,
            'created_at': note.created_at.isoformat(),
            'updated_at': note.updated_at.isoformat()
        } for note in notes]
    })


# =============================================================================
# MOBILE API ROUTES
# =============================================================================

@app.route('/api/mobile/login', methods=['POST'])
def mobile_login():
    """Login per app mobile"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({
                'success': False,
                'message': 'Username e password richiesti'
            }), 400

        user = User.query.filter_by(username=username, password=password).first()

        if not user:
            return jsonify({
                'success': False,
                'message': 'Credenziali errate'
            }), 401

        # Genera wallet se non esiste
        if not user.wallet_address:
            user.wallet_address = blockchain.generate_wallet_address(user.id)
            db.session.commit()

        # Genera token
        token = generate_token(user.id)

        # Ricompensa login
        blockchain.reward_user(user, blockchain.login_reward, 'login')

        response_data = {
            'success': True,
            'message': 'Login effettuato',
            'data': {
                'id': user.id,
                'username': user.username,
                'wallet_address': user.wallet_address,
                'balance': user.balance,
                'total_earned': user.total_earned,
                'created_at': user.created_at.isoformat()
            }
        }

        response = jsonify(response_data)
        response.headers['Authorization'] = f'Bearer {token}'
        return response

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Errore server: {str(e)}'
        }), 500


@app.route('/api/mobile/validate', methods=['GET'])
@token_required
def mobile_validate(current_user):
    """Valida token e restituisce dati utente"""
    return jsonify({
        'success': True,
        'data': {
            'id': current_user.id,
            'username': current_user.username,
            'wallet_address': current_user.wallet_address,
            'balance': current_user.balance,
            'total_earned': current_user.total_earned,
            'created_at': current_user.created_at.isoformat()
        }
    })


@app.route('/api/mobile/wallet', methods=['GET'])
@token_required
def mobile_wallet(current_user):
    """Dati wallet per mobile"""
    try:
        # Ottieni transazioni recenti
        recent_transactions = Transaction.query.filter_by(to_wallet=current_user.wallet_address) \
            .order_by(Transaction.timestamp.desc()) \
            .limit(10).all()

        transactions_data = []
        for tx in recent_transactions:
            transactions_data.append({
                'tx_hash': tx.tx_hash,
                'amount': tx.amount,
                'tx_type': tx.tx_type,
                'timestamp': tx.timestamp.isoformat(),
                'confirmed': tx.confirmed
            })

        return jsonify({
            'success': True,
            'data': {
                'wallet_address': current_user.wallet_address,
                'balance': current_user.balance,
                'total_earned': current_user.total_earned,
                'recent_transactions': transactions_data
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Errore: {str(e)}'
        }), 500


@app.route('/api/mobile/notes', methods=['GET'])
@token_required
def mobile_get_notes(current_user):
    """Ottieni note utente per mobile"""
    try:
        notes = UserNote.query.filter_by(user_id=current_user.id) \
            .order_by(UserNote.updated_at.desc()).all()

        notes_data = []
        for note in notes:
            notes_data.append({
                'id': note.id,
                'title': note.title,
                'content': note.content,
                'note_type': note.note_type,
                'priority': note.priority,
                'tags': note.tags,
                'external_url': note.external_url,
                'due_date': note.due_date.isoformat() if note.due_date else None,
                'completed': note.completed,
                'created_at': note.created_at.isoformat(),
                'updated_at': note.updated_at.isoformat()
            })

        return jsonify({
            'success': True,
            'data': notes_data
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Errore: {str(e)}'
        }), 500


@app.route('/api/mobile/notes', methods=['POST'])
@token_required
def mobile_create_note(current_user):
    """Crea nota da mobile con ricompensa ADG"""
    try:
        data = request.get_json()

        note = UserNote(
            user_id=current_user.id,
            title=data.get('title'),
            content=data.get('content'),
            note_type=data.get('note_type', 'text'),
            priority=data.get('priority', 'normal'),
            tags=data.get('tags', ''),
            external_url=data.get('external_url')
        )

        # Due date se fornita
        if data.get('due_date'):
            try:
                note.due_date = datetime.fromisoformat(data.get('due_date'))
            except:
                pass

        db.session.add(note)
        db.session.commit()

        # RICOMPENSA ADG PER CREAZIONE NOTA DA MOBILE
        blockchain.reward_user(current_user, blockchain.note_creation_reward, 'note_creation')

        return jsonify({
            'success': True,
            'message': f'Nota creata! +{blockchain.note_creation_reward} ADG',
            'adg_earned': blockchain.note_creation_reward,
            'data': {
                'id': note.id,
                'title': note.title,
                'content': note.content,
                'note_type': note.note_type,
                'priority': note.priority,
                'created_at': note.created_at.isoformat(),
                'updated_at': note.updated_at.isoformat()
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Errore: {str(e)}'
        }), 500


@app.route('/api/mobile/upload', methods=['POST'])
@token_required
def mobile_upload_file(current_user):
    """Upload file da mobile con ricompensa ADG"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'Nessun file'})

        file = request.files['file']

        if file.filename == '':
            return jsonify({'success': False, 'message': 'File vuoto'})

        if not allowed_file(file.filename):
            return jsonify({'success': False, 'message': 'Tipo file non supportato'})

        # Genera nome sicuro
        original_filename = file.filename
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        safe_filename = f"{uuid.uuid4().hex}.{file_extension}"

        # Salva file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
        file.save(file_path)

        # Salva nel database
        user_file = UserFile(
            user_id=current_user.id,
            filename=safe_filename,
            original_filename=original_filename,
            file_type=get_file_type(original_filename),
            file_size=os.path.getsize(file_path),
            file_path=file_path,
            mime_type=file.mimetype
        )

        db.session.add(user_file)
        db.session.commit()

        # RICOMPENSA ADG PER UPLOAD FILE DA MOBILE
        blockchain.reward_user(current_user, blockchain.file_upload_reward, 'file_upload')

        return jsonify({
            'success': True,
            'message': f'File caricato! +{blockchain.file_upload_reward} ADG',
            'adg_earned': blockchain.file_upload_reward,
            'data': {
                'id': user_file.id,
                'original_filename': user_file.original_filename,
                'file_type': user_file.file_type,
                'file_size': user_file.file_size,
                'uploaded_at': user_file.uploaded_at.isoformat()
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Errore: {str(e)}'
        }), 500


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
    print(f"Upload Folder: {UPLOAD_FOLDER}")
    print("Funzionalità integrate:")
    print("  - Sistema File Upload completo con ricompense ADG")
    print("  - Sistema Note con priorità, tag e ricompense ADG")
    print("  - Ricompense per completamento task")
    print("  - API Mobile per Unity App con ricompense")
    print("  - JWT Authentication")
    print("  - Blockchain ADG Token")
    print("Ricompense ADG:")
    print(f"  - Upload file: {blockchain.file_upload_reward} ADG")
    print(f"  - Creazione nota: {blockchain.note_creation_reward} ADG")
    print(f"  - Completamento task: {blockchain.note_completion_reward} ADG")
    print("Nota: Per produzione utilizzare Gunicorn")
    print("=" * 60)

    app.run(debug=True, host='0.0.0.0', port=5000)