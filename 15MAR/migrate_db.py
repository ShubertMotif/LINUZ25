from app5 import app, db

with app.app_context():
    db.create_all()
    print("✅ Database creato o aggiornato con successo.")
    print("✅ APP5.")
