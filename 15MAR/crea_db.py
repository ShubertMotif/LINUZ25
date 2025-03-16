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

def create_database():
    """Crea il database e le tabelle basandosi sui modelli definiti."""
    db.create_all()
    print("Database creato con successo!")

if __name__ == '__main__':
    with app.app_context():
        create_database()
