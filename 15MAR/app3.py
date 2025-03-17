from flask import Flask, request, render_template, jsonify,json,redirect
from flask_sqlalchemy import SQLAlchemy
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
import logging
import time
import os
from pypdf import PdfReader


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'DATA', 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

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





tokenizer = AutoTokenizer.from_pretrained("GroNLP/gpt2-medium-italian-embeddings")
model = AutoModelForCausalLM.from_pretrained("GroNLP/gpt2-medium-italian-embeddings")
model.to("cpu")
generator = pipeline("text-generation", model=model, tokenizer=tokenizer)

################ FUNZIONI



def load_config(config_type):
    # Seleziona il file di configurazione corretto in base al tipo
    if config_type == 'short':
        config_file = 'config_short.json'
    elif config_type == 'large':
        config_file = 'config_large.json'
    else:
        config_file = 'config_medium.json'

    config_path = f'static/config/{config_file}'
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"Configuration file not found: {config_path}")
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from the configuration file: {config_path}")
    return None



def save_interaction(user_input, bot_response, feedback=None, model_used="Default Model"):
    interaction = Interaction(
        user_input=user_input,
        bot_response=bot_response,
        feedback=feedback,
        model_used=model_used
    )
    db.session.add(interaction)
    db.session.commit()

    # Calcolo della dimensione del database (numero di interazioni)
    interaction_count = Interaction.query.count()
    print(f"Numero totale di interazioni nel database: {interaction_count}")

    # Stampa un estratto di ciò che è stato appena salvato
    print(
        f"Ultima interazione salvata: Input: {interaction.user_input}, Output: {interaction.bot_response}, Feedback: {interaction.feedback}")



def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ''
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:  # Assicurati che il testo non sia None
            text += page_text + ' '
    return text

def fetch_wiki_summary(topic):
    url = f"https://it.wikipedia.org/wiki/{topic}"
    response = requests.get(url)
    if response.status_code != 200:
        return "Contenuto non trovato o errore nella richiesta."

    soup = BeautifulSoup(response.content, 'html.parser')
    content = ''
    for p in soup.find_all('p'):
        if len(content) < 90:
            content += p.text + ' '
        else:
            break
    return content[:90]  # Limita a 90 parole per assicurare il rispetto delle linee guida


######### MACHINE LEARNING

from transformers import BertTokenizer, BertForSequenceClassification
from torch.utils.data import DataLoader, RandomSampler, SequentialSampler, TensorDataset
import torch

# Carica il tokenizer e il modello
#tokenizerML = BertTokenizer.from_pretrained('bert-base-uncased')
#modelML= BertForSequenceClassification.from_pretrained('bert-base-uncased', num_labels=2)

#train_dataset=0

# Supponiamo che `train_dataset` sia il tuo dataset etichettato
#train_sampler = RandomSampler(train_dataset)
#train_dataloader = DataLoader(train_dataset, sampler=train_sampler, batch_size=32)

## Funzione di training
#def train(epoch, model, dataloader):
#    modelML.train()
#
#    for batch in dataloader:
#        inputs = {'input_ids': batch[0], 'attention_mask': batch[1], 'labels': batch[2]}
#        modelML.zero_grad()
#        outputs = model(**inputs)
#       loss = outputs[0]
#        loss.backward()
#        optimizer.step()
#
# Esempio di addestramento
#optimizer = torch.optim.Adam(modelML.parameters(), lr=2e-5)
#for epoch in range(1, 4):  # numero di epoche
#    train(epoch, modelML, train_dataloader)


############## CODA DI ELABORAZIONE

import queue
import threading

data_to_process=[]

def process_data(item):
    return print('Queue +1')


def worker(queue):
    while True:
        item = queue.get()
        if item is None:
            break
        process_data(item)  # Sostituisci questa funzione con il tuo processo
        queue.task_done()

# Crea una coda e un thread pool
q = queue.Queue()
threads = []
for i in range(4):  # Numero di thread
    t = threading.Thread(target=worker, args=(q,))
    t.start()
    threads.append(t)

# Aggiungi compiti alla coda
for item in data_to_process:
    q.put(item)

# Blocca fino a quando tutti i compiti nella coda sono stati presi in carico
q.join()

# Ferma i worker
for i in range(4):
    q.put(None)
for t in threads:
    t.join()




####### RUOTE

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        user_input = request.form.get('user_input')
        config = load_config(request.form.get('config_type'))
        if not config:
            return render_template('index.html', error="Failed to load configuration.")
        try:
            start_time = time.time()
            response = generator(user_input, truncation=config['truncation'], max_length=config['max_length'],
                                 temperature=config['temperature'], top_p=0.9,
                                 num_return_sequences=config['num_return_sequences'],
                                 max_new_tokens=config.get('max_new_token', 50))[0]['generated_text']
            save_interaction(user_input, response)
            return render_template('index.html', output=response, user_input=user_input, generation_time=time.time() - start_time)
        except Exception as e:
            logging.error(f"Error generating text: {e}")
            return render_template('index.html', error=str(e))
    return render_template('index.html')

@app.route('/feedback', methods=['POST'])
def feedback():
    user_input = request.form.get('user_input', '')
    response = request.form.get('response', '')
    feedback = request.form.get('feedback', '')
    model_used = "GPT-2 Medium"  # or fetch dynamically based on your application logic

    if user_input and response and feedback:
        save_interaction(user_input, response, feedback, model_used)
        return redirect('/thank_you')
    else:
        return render_template('index.html', error="Missing required feedback data.")


@app.route('/thank_you')
def thank_you():
    return render_template('thank_you.html')



@app.route('/extract-text', methods=['POST'])
def extract_text():
    if 'file' not in request.files:
        return render_template('index.html', error="Nessun file selezionato.")

    pdf_file = request.files['file']
    if pdf_file.filename == '':
        return render_template('index.html', error="Nessun file selezionato.")

    if pdf_file and pdf_file.filename.endswith('.pdf'):
        pdf_path = os.path.join('training_data', 'PDF', pdf_file.filename)
        pdf_file.save(pdf_path)
        extracted_text = extract_text_from_pdf(pdf_path)

        # Usa il testo estratto come input per GPT
        config = load_config(request.form.get('config_type'))  # Scegli la configurazione desiderata
        if config:
            response = generator(extracted_text, truncation=config['truncation'], max_length=config['max_length'],
                                 temperature=config['temperature'], top_p=0.9,
                                 num_return_sequences=config['num_return_sequences'],
                                 max_new_tokens=config.get('max_new_token', 50))[0]['generated_text']

            return render_template('index.html', output=response, user_input=extracted_text,
                                   generation_time=0)  # generation_time può essere omesso o calcolato se necessario
        else:
            return render_template('index.html', error="Failed to load model configuration.")
    else:
        return render_template('index.html', error="Formato file non supportato.")


@app.route('/analyze-wikipedia', methods=['GET', 'POST'])
def analyze_wikipedia():
    if request.method == 'POST':
        keyword = request.form.get('keyword')
        if not keyword:
            return render_template('index.html', error="Nessuna parola chiave fornita.")

        summary = fetch_wiki_summary(keyword)
        if len(summary) > 500:
            summary = summary[:500]  # Assicurati che la lunghezza non superi 90 parole

        config = load_config('short')  # Puoi scegliere una configurazione appropriata
        if not config:
            return render_template('index.html', error="Configurazione non caricata correttamente.")

        try:
            response = generator(summary, truncation=config['truncation'], max_length=config['max_length'],
                                 temperature=config['temperature'], top_p=0.9,
                                 num_return_sequences=config['num_return_sequences'],
                                 max_new_tokens=config.get('max_new_token', 50))[0]['generated_text']
            return render_template('index.html', output=response, user_input=summary)
        except Exception as e:
            logging.error(f"Errore durante la generazione del testo: {e}")
            return render_template('index.html', error="Errore nella generazione del testo.")

    return render_template('analyze_wikipedia.html')  # Crea un template HTML per questa funzione

@app.route('/database')
def database_view():
    # Recupera tutte le interazioni dal database, ordinate in modo decrescente per ID
    interactions = Interaction.query.order_by(Interaction.id.desc()).all()
    return render_template('database.html', interactions=interactions)



@app.route('/add-military-info', methods=['GET', 'POST'])
def add_military_info():
    if request.method == 'POST':
        # Raccolta di tutti i dati del form
        data = {
            'country_name': request.form['country_name'],
            'population': request.form['population'],
            'military_personnel': request.form['military_personnel'],
            'under_age_population': request.form['under_age_population'],
            'gdp': request.form['gdp'],
            'tanks': request.form['tanks'],
            'aircraft_carriers': request.form['aircraft_carriers'],
            'military_spending': request.form['military_spending'],
            'submarines': request.form['submarines'],
            'fighter_aircraft': request.form['fighter_aircraft'],
            'nuclear_weapons': request.form['nuclear_weapons'],
            'military_satellites': request.form['military_satellites'],
            'cyber_defense_capability': request.form['cyber_defense_capability'],
            'active_reservists': request.form['active_reservists'],
            'paramilitary_units': request.form['paramilitary_units'],
            'defense_budget_as_percentage_of_gdp': request.form['defense_budget_as_percentage_of_gdp'],
            'annual_defense_budget_growth': request.form['annual_defense_budget_growth'],
            'total_border_length': request.form['total_border_length'],
            'coastline_length': request.form['coastline_length'],
            'strategic_alliances': request.form['strategic_alliances']
        }

        # Creazione e salvataggio del nuovo record
        new_info = MilitaryInfo(**data)
        db.session.add(new_info)
        db.session.commit()

        return redirect('/military-info')  # Redirect a una pagina di conferma o di visualizzazione delle informazioni
    return render_template('add_military_info.html')


@app.route('/military-info')
def military_info():
    info = MilitaryInfo.query.all()
    return render_template('military_info.html', info=info)





if __name__ == '__main__':
    app.run(debug=True, port=5000)
