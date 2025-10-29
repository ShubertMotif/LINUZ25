# blockchain_system.py
import hashlib
import json
import time
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional
import threading
import queue
from decimal import Decimal
import sqlite3
import uuid

@dataclass
class Token:
    """Rappresenta un token del sistema"""
    id: str
    owner: str
    amount: Decimal
    created_at: datetime
    source: str  # 'mining', 'purchase', 'reward'
    processed_by_gpu: bool = False

@dataclass
class Transaction:
    """Transazione blockchain"""
    id: str
    from_address: str
    to_address: str
    amount: Decimal
    timestamp: datetime
    tx_type: str  # 'mining', 'transfer', 'purchase'
    signature: str
    block_hash: Optional[str] = None

class Block:
    """Blocco della blockchain"""
    def __init__(self, index: int, transactions: List[Transaction], 
                 previous_hash: str, nonce: int = 0):
        self.index = index
        self.timestamp = datetime.now()
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        """Calcola l'hash del blocco"""
        block_string = json.dumps({
            'index': self.index,
            'timestamp': self.timestamp.isoformat(),
            'transactions': [vars(tx) for tx in self.transactions],
            'previous_hash': self.previous_hash,
            'nonce': self.nonce
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

class GPUMiner:
    """Simulatore mining GPU RTX 3060"""
    def __init__(self):
        self.is_mining = False
        self.hash_rate = 25_000_000  # 25 MH/s per RTX 3060
        self.processing_queue = queue.Queue()
        self.processed_tokens = []

    def start_mining(self):
        """Avvia il processo di mining"""
        self.is_mining = True
        mining_thread = threading.Thread(target=self._mine_loop)
        mining_thread.daemon = True
        mining_thread.start()

    def _mine_loop(self):
        """Loop principale del mining"""
        while self.is_mining:
            try:
                # Processa token dalla coda
                token = self.processing_queue.get(timeout=1)
                processing_time = self._calculate_processing_time(token.amount)
                
                print(f"GPU Mining: Processando {token.amount} token per utente {token.owner}")
                time.sleep(processing_time)  # Simula il tempo di processing
                
                token.processed_by_gpu = True
                self.processed_tokens.append(token)
                
                print(f"GPU Mining: Completato processing per {token.owner}")
                
            except queue.Empty:
                continue

    def _calculate_processing_time(self, amount: Decimal) -> float:
        """Calcola il tempo di processing basato sulla quantità"""
        # Più token = più tempo di processing
        base_time = 2.0  # 2 secondi base
        return base_time + (float(amount) / 1000.0)

    def add_to_processing(self, token: Token):
        """Aggiunge token alla coda di processing"""
        self.processing_queue.put(token)

class TokenSaleManager:
    """Gestisce le vendite a tranche"""
    def __init__(self):
        self.total_supply = 10_000_000
        self.tranches = [
            {'name': 'Tranche 1', 'tokens': 1_000_000, 'price_usdt': 0.01, 'sold': 0},
            {'name': 'Tranche 2', 'tokens': 1_500_000, 'price_usdt': 0.015, 'sold': 0},
            {'name': 'Tranche 3', 'tokens': 2_000_000, 'price_usdt': 0.02, 'sold': 0},
            {'name': 'Tranche 4', 'tokens': 2_500_000, 'price_usdt': 0.025, 'sold': 0},
            {'name': 'Tranche 5', 'tokens': 3_000_000, 'price_usdt': 0.03, 'sold': 0}
        ]
        self.current_tranche = 0

    def get_current_price(self) -> Decimal:
        """Ottiene il prezzo corrente"""
        if self.current_tranche < len(self.tranches):
            return Decimal(str(self.tranches[self.current_tranche]['price_usdt']))
        return Decimal('0.05')  # Prezzo finale

    def can_purchase(self, amount: int) -> bool:
        """Verifica se è possibile acquistare"""
        if self.current_tranche >= len(self.tranches):
            return False
        
        tranche = self.tranches[self.current_tranche]
        return (tranche['sold'] + amount) <= tranche['tokens']

    def record_purchase(self, amount: int):
        """Registra un acquisto"""
        if self.current_tranche < len(self.tranches):
            self.tranches[self.current_tranche]['sold'] += amount
            
            # Passa alla tranche successiva se completata
            if self.tranches[self.current_tranche]['sold'] >= self.tranches[self.current_tranche]['tokens']:
                self.current_tranche += 1

class UserActivityTracker:
    """Traccia le attività degli utenti per rewards"""
    def __init__(self):
        self.user_sessions = {}
        self.activity_multipliers = {
            'login': 1,
            'post': 5,
            'comment': 2,
            'like': 1,
            'share': 3,
            'profile_complete': 10
        }

    def track_session(self, user_id: str):
        """Inizia il tracking di una sessione"""
        self.user_sessions[user_id] = {
            'start_time': datetime.now(),
            'activities': [],
            'tokens_earned': 0
        }

    def record_activity(self, user_id: str, activity_type: str):
        """Registra un'attività"""
        if user_id in self.user_sessions:
            self.user_sessions[user_id]['activities'].append({
                'type': activity_type,
                'timestamp': datetime.now(),
                'tokens': self.activity_multipliers.get(activity_type, 1)
            })

    def calculate_session_rewards(self, user_id: str) -> int:
        """Calcola i token guadagnati in una sessione"""
        if user_id not in self.user_sessions:
            return 0

        session = self.user_sessions[user_id]
        
        # Token per attività
        activity_tokens = sum(act['tokens'] for act in session['activities'])
        
        # Token per tempo speso (1 token ogni 10 minuti)
        time_spent = datetime.now() - session['start_time']
        time_tokens = int(time_spent.total_seconds() / 600)  # 10 minuti = 600 secondi
        
        total_tokens = activity_tokens + time_tokens
        session['tokens_earned'] = total_tokens
        
        return total_tokens

class Blockchain:
    """Blockchain principale"""
    def __init__(self):
        self.chain = [self._create_genesis_block()]
        self.pending_transactions = []
        self.mining_reward = 100
        self.difficulty = 4

    def _create_genesis_block(self) -> Block:
        """Crea il blocco genesis"""
        genesis_tx = Transaction(
            id=str(uuid.uuid4()),
            from_address="genesis",
            to_address="system",
            amount=Decimal('10000000'),
            timestamp=datetime.now(),
            tx_type="genesis",
            signature="genesis_signature"
        )
        return Block(0, [genesis_tx], "0")

    def add_transaction(self, transaction: Transaction):
        """Aggiunge una transazione"""
        self.pending_transactions.append(transaction)

    def mine_pending_transactions(self, mining_reward_address: str) -> Block:
        """Mina le transazioni in sospeso"""
        reward_transaction = Transaction(
            id=str(uuid.uuid4()),
            from_address="system",
            to_address=mining_reward_address,
            amount=Decimal(str(self.mining_reward)),
            timestamp=datetime.now(),
            tx_type="mining_reward",
            signature="system_signature"
        )

        block = Block(
            len(self.chain),
            self.pending_transactions + [reward_transaction],
            self.chain[-1].hash
        )

        # Proof of work semplificato
        while not block.hash.startswith('0' * self.difficulty):
            block.nonce += 1
            block.hash = block.calculate_hash()

        self.chain.append(block)
        self.pending_transactions = []
        return block

class TokenEcosystem:
    """Sistema completo dell'ecosistema token"""
    def __init__(self):
        self.blockchain = Blockchain()
        self.gpu_miner = GPUMiner()
        self.sale_manager = TokenSaleManager()
        self.activity_tracker = UserActivityTracker()
        self.user_balances = {}
        
        # Database per persistenza
        self.init_database()
        
        # Avvia il mining
        self.gpu_miner.start_mining()

    def init_database(self):
        """Inizializza il database SQLite"""
        self.conn = sqlite3.connect('blockchain.db', check_same_thread=False)
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                balance REAL DEFAULT 0,
                total_earned REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                from_address TEXT,
                to_address TEXT,
                amount REAL,
                tx_type TEXT,
                timestamp TIMESTAMP,
                block_hash TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS token_sales (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                amount REAL,
                usdt_paid REAL,
                tranche INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()

    def register_user(self, user_id: str):
        """Registra un nuovo utente"""
        cursor = self.conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO users (id) VALUES (?)', (user_id,))
        self.conn.commit()
        self.user_balances[user_id] = Decimal('0')

    def reward_user_activity(self, user_id: str, activity_type: str):
        """Ricompensa l'attività dell'utente"""
        self.activity_tracker.record_activity(user_id, activity_type)
        tokens_earned = self.activity_tracker.calculate_session_rewards(user_id)
        
        if tokens_earned > 0:
            # Crea token per l'utente
            token = Token(
                id=str(uuid.uuid4()),
                owner=user_id,
                amount=Decimal(str(tokens_earned)),
                created_at=datetime.now(),
                source='reward'
            )
            
            # Invia alla GPU per processing
            self.gpu_miner.add_to_processing(token)
            
            return tokens_earned
        return 0

    def process_token_purchase(self, user_id: str, token_amount: int, usdt_amount: Decimal) -> bool:
        """Processa l'acquisto di token"""
        if not self.sale_manager.can_purchase(token_amount):
            return False
        
        # Verifica il pagamento USDT
        expected_cost = self.sale_manager.get_current_price() * token_amount
        if usdt_amount < expected_cost:
            return False
        
        # Registra la vendita
        self.sale_manager.record_purchase(token_amount)
        
        # Crea transazione
        transaction = Transaction(
            id=str(uuid.uuid4()),
            from_address="sale_pool",
            to_address=user_id,
            amount=Decimal(str(token_amount)),
            timestamp=datetime.now(),
            tx_type="purchase",
            signature=f"purchase_{user_id}_{int(time.time())}"
        )
        
        self.blockchain.add_transaction(transaction)
        
        # Crea token per processing GPU
        token = Token(
            id=str(uuid.uuid4()),
            owner=user_id,
            amount=Decimal(str(token_amount)),
            created_at=datetime.now(),
            source='purchase'
        )
        
        self.gpu_miner.add_to_processing(token)
        
        # Salva nel database
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO token_sales (id, user_id, amount, usdt_paid, tranche)
            VALUES (?, ?, ?, ?, ?)
        ''', (str(uuid.uuid4()), user_id, float(token_amount), 
              float(usdt_amount), self.sale_manager.current_tranche))
        self.conn.commit()
        
        return True

    def get_user_balance(self, user_id: str) -> Decimal:
        """Ottiene il bilancio dell'utente"""
        # Controlla i token processati dalla GPU
        user_processed_tokens = [
            token for token in self.gpu_miner.processed_tokens 
            if token.owner == user_id
        ]
        
        total_balance = sum(token.amount for token in user_processed_tokens)
        return total_balance

    def get_system_stats(self) -> Dict:
        """Ottiene le statistiche del sistema"""
        return {
            'total_blocks': len(self.blockchain.chain),
            'pending_transactions': len(self.blockchain.pending_transactions),
            'current_tranche': self.sale_manager.current_tranche + 1,
            'current_price_usdt': float(self.sale_manager.get_current_price()),
            'tokens_in_processing': self.gpu_miner.processing_queue.qsize(),
            'tokens_processed': len(self.gpu_miner.processed_tokens),
            'gpu_mining_active': self.gpu_miner.is_mining
        }

# Esempio di integrazione Flask
"""
from flask import Flask, request, jsonify
from blockchain_system import TokenEcosystem

app = Flask(__name__)
ecosystem = TokenEcosystem()

@app.route('/api/register', methods=['POST'])
def register_user():
    user_id = request.json.get('user_id')
    ecosystem.register_user(user_id)
    ecosystem.activity_tracker.track_session(user_id)
    return jsonify({'success': True, 'message': 'User registered'})

@app.route('/api/activity', methods=['POST'])
def record_activity():
    user_id = request.json.get('user_id')
    activity = request.json.get('activity')
    tokens_earned = ecosystem.reward_user_activity(user_id, activity)
    return jsonify({'tokens_earned': tokens_earned})

@app.route('/api/purchase', methods=['POST'])
def purchase_tokens():
    user_id = request.json.get('user_id')
    token_amount = request.json.get('token_amount')
    usdt_amount = Decimal(str(request.json.get('usdt_amount')))
    
    success = ecosystem.process_token_purchase(user_id, token_amount, usdt_amount)
    return jsonify({'success': success})

@app.route('/api/balance/<user_id>')
def get_balance(user_id):
    balance = ecosystem.get_user_balance(user_id)
    return jsonify({'balance': float(balance)})

@app.route('/api/stats')
def get_stats():
    return jsonify(ecosystem.get_system_stats())

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
"""