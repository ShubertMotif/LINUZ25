from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.dirname(__file__), 'DATA', 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Assicurati che tutti i modelli siano importati qui
# from your_application.models import User, Photo, Offerta, Message

from datetime import datetime

class Interaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_input = db.Column(db.String(500), nullable=False)
    bot_response = db.Column(db.String(500), nullable=False)
    feedback = db.Column(db.String(100))
    model_used = db.Column(db.String(100), nullable=False)  # Nome del modello GPT usato
    config_details = db.Column(db.String(500))  # Dettagli della configurazione usata, es. JSON string
    generation_time = db.Column(db.Float)  # Tempo impiegato per generare la risposta
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Data e ora di creazione dell'interazione
    additional_info = db.Column(db.Text)  # Campo opzionale per ulteriori informazioni o note

    def __repr__(self):
        return f'<Interaction {self.id} - {self.user_input}>'



class MilitaryInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    country_name = db.Column(db.String(100), nullable=False, unique=True)
    population = db.Column(db.BigInteger)
    military_personnel = db.Column(db.Integer)
    under_age_population = db.Column(db.BigInteger)
    gdp = db.Column(db.BigInteger)
    tanks = db.Column(db.Integer)
    aircraft_carriers = db.Column(db.Integer)
    military_spending = db.Column(db.BigInteger)
    submarines = db.Column(db.Integer)
    fighter_aircraft = db.Column(db.Integer)
    nuclear_weapons = db.Column(db.Integer)
    military_satellites = db.Column(db.Integer)
    cyber_defense_capability = db.Column(db.String(100))
    active_reservists = db.Column(db.Integer)
    paramilitary_units = db.Column(db.Integer)
    defense_budget_as_percentage_of_gdp = db.Column(db.Float)
    annual_defense_budget_growth = db.Column(db.Float)
    total_border_length = db.Column(db.Integer)
    coastline_length = db.Column(db.Integer)
    strategic_alliances = db.Column(db.String(500))

    def __repr__(self):
        return f'<MilitaryInfo {self.country_name}>'

def create_database():
    """Crea il database e le tabelle basandosi sui modelli definiti."""
    db.create_all()
    print("Database creato con successo!")

if __name__ == '__main__':
    with app.app_context():
        create_database()
