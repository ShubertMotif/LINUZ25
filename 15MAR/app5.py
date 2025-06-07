from xml.dom.minidom import Document

from flask import Flask, request, render_template, jsonify,json,redirect,session
from flask_sqlalchemy import SQLAlchemy
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
import logging
import time
import os
from pypdf import PdfReader

import json
import time

from transformers import BertTokenizer, BertForSequenceClassification
from torch.utils.data import DataLoader, SequentialSampler, TensorDataset



app = Flask(__name__)
app.config['SECRET_KEY'] = 'SKYNET'
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




class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    full_text = db.Column(db.Text, nullable=False)  # Tutto il testo estratto
    summary = db.Column(db.Text)  # Riassunto complessivo
    block_texts = db.Column(db.Text)  # Testo dei blocchi separati (come stringa unica, con separatori)
    block_summaries = db.Column(db.Text)  # Riassunti blocchi (es. Blocco 1:\nRiassunto...)
    keywords = db.Column(db.String(500))  # Parole chiave (tutte insieme)
    num_blocks = db.Column(db.Integer)  # Numero di blocchi elaborati
    processing_time = db.Column(db.Float)  # Secondi impiegati
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Document {self.filename} - {self.num_blocks} blocchi>"




#############PYTORCH

import torch
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


#MODEL TRASFORMER

tokenizer = AutoTokenizer.from_pretrained("GroNLP/gpt2-medium-italian-embeddings")
model = AutoModelForCausalLM.from_pretrained("GroNLP/gpt2-medium-italian-embeddings").to(device)
generator = pipeline("text-generation", model=model, tokenizer=tokenizer, device=0 if device.type == "cuda" else -1)

tokenizerBERT = BertTokenizer.from_pretrained('dbmdz/bert-base-italian-uncased')
modelBERT = BertForSequenceClassification.from_pretrained('dbmdz/bert-base-italian-uncased').to(device)

from transformers import MBartForConditionalGeneration, MBart50TokenizerFast

modelMBART = MBartForConditionalGeneration.from_pretrained("facebook/mbart-large-50-many-to-many-mmt").to(device)
tokenizerMBART = MBart50TokenizerFast.from_pretrained("facebook/mbart-large-50-many-to-many-mmt")


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


def save_interaction(user_input, bot_response, feedback, model_used, summary='', config_details='', generation_time=0.0):
    interaction = Interaction(
        user_input=user_input,
        bot_response=bot_response,
        feedback=feedback,
        model_used=model_used,
        additional_info=summary,  # This field stores the summary
        config_details=config_details,  # Optional details about configuration
        generation_time=generation_time  # Default to 0 if not specified
    )
    db.session.add(interaction)
    db.session.commit()

    # Diagnostic printouts
    print(f"Numero totale di interazioni nel database: {Interaction.query.count()}")
    #print(f"Ultima interazione salvata: Input: {interaction.user_input}, Output: {interaction.bot_response}, Feedback: {interaction.feedback}, Model Used: {interaction.model_used}, Config Details: {interaction.config_details}, Summary: {interaction.additional_info}")


    # Print the count of interactions and details of the most recently saved interaction
    interaction_count = Interaction.query.count()
    print(f"Numero totale di interazioni nel database: {interaction_count}")
    print(f"Ultima interazione salvata: Input: {interaction.user_input}, Output: {interaction.bot_response}, Feedback: {interaction.feedback}, Model Used: {interaction.model_used}, Config Details: {interaction.config_details}")


def extract_text_from_pdf_blocchi(pdf_path, pages_per_block=20):
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    blocchi = []

    for start in range(0, total_pages, pages_per_block):
        end = min(start + pages_per_block, total_pages)
        testo_blocco = ''
        for page in reader.pages[start:end]:
            testo = page.extract_text()
            if testo:
                testo_blocco += testo + ' '
        if testo_blocco.strip():
            blocchi.append(testo_blocco.strip())

    return blocchi




def fetch_wiki_summaries(topic):
    search_url = f"https://it.wikipedia.org/w/index.php?search={topic}"
    response = requests.get(search_url)
    print("Status Code:", response.status_code)  # Print the status code of the response

    if response.status_code != 200:
        return "Contenuto non trovato o errore nella richiesta."

    # Print the first 500 characters of the response content to get an idea of what was fetched
    print("Response Content (snippet):", response.text[:500] + '...')

    soup = BeautifulSoup(response.content, 'html.parser')
    summaries = []

    # Find all paragraphs in the search page
    for p in soup.find_all('p', limit=5):  # Limit to 5 to prevent too many results
        text = p.get_text()
        if text:
            # Limit the text to 90 words for guidelines respect
            shortened_text = ' '.join(text.split()[:90]) + '...'
            summaries.append(shortened_text)

    return summaries

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
    summary = request.form.get('summary', '')
    feedback = request.form.get('feedback', '')
    model_used = "MBart"  # Update according to the model you're actually using for summarization

    if user_input and response and feedback:
        save_interaction(user_input=user_input, bot_response=response, feedback=feedback, model_used=model_used, summary=summary)
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






def fetch_wiki_summaries(keyword):
    search_url = f"https://it.wikipedia.org/w/index.php?search={keyword}"
    response = requests.get(search_url)
    if response.status_code != 200:
        return None

    soup = BeautifulSoup(response.content, 'html.parser')
    summaries = []
    for p in soup.find_all('p', limit=5):  # Aumenta il limite se necessario
        text = p.get_text()
        if text:
            summaries.append(text)

    full_text = ' '.join(summaries)
    return full_text[:1024]  # Limita il testo a 1024 caratteri per MBART


def summarize_text(text, max_tokens=1024, max_summary_tokens=512):
    print("[MBART] Avvio riassunto...")

    tokenizerMBART.src_lang = "it_IT"

    # Tokenizza input interamente e tronca in token, non caratteri
    inputs = tokenizerMBART(
        text,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=max_tokens
    ).to(device)

    # Genera il riassunto con MBART
    summary_ids = modelMBART.generate(
        inputs['input_ids'],
        forced_bos_token_id=tokenizerMBART.lang_code_to_id["it_IT"],
        num_beams=5,
        length_penalty=1.0,
        max_length=max_summary_tokens,
        min_length=100,
        no_repeat_ngram_size=3,
        early_stopping=True
    )

    summary = tokenizerMBART.decode(summary_ids[0], skip_special_tokens=True)
    print(f"[MBART] Riassunto generato ({len(summary)} caratteri): {summary[:200]}{'...' if len(summary) > 200 else ''}")
    return summary


@app.route('/analyze-wikipedia', methods=['GET', 'POST'])
def analyze_wikipedia():
    if request.method == 'POST':
        keyword = request.form.get('keyword')
        if not keyword:
            return render_template('index.html', error="Nessuna parola chiave fornita.")

        print('KEYWORD',keyword)
        time.sleep(2)

        content = fetch_wiki_summaries(keyword)
        print('CONTENT', content)
        time.sleep(2)
        if not content:
            return render_template('index.html', error="Errore nel recupero del contenuto.")

        summary = summarize_text(content)

        print('SUMMARY MBART', summary)
        time.sleep(2)

        # Save the interaction to the database
        save_interaction(user_input=content, bot_response=summary, feedback='Pending', model_used='MBart')

        # Make sure to pass the summary properly to the template
        return render_template('index.html', output=summary, user_input=content, summary=summary)

    # Display the form if no POST request has been made
    return render_template('analyze_wikipedia.html')



@app.route('/queue-analysis', methods=['GET', 'POST'])
def queue_analysis():
    if request.method == 'POST':
        keywords = request.form.get('keywords', '').split(',')
        summaries = []
        for keyword in keywords:
            keyword = keyword.strip()
            content = fetch_wiki_summaries(keyword)
            if content:
                summary = summarize_text(content)
                summaries.append({'keyword': keyword, 'content': content, 'summary': summary})
        session['summaries'] = summaries
        return redirect(url_for('feedback_collect'))
    return render_template('queue_analysis.html')


from flask import redirect, url_for

@app.route('/feedback-collect', methods=['GET', 'POST'])
def feedback_collect():
    if request.method == 'POST':
        summaries = session.pop('summaries', [])  # Use pop to clear them after processing
        for index, summary in enumerate(summaries):
            feedback = request.form.get(f'feedback_{index+1}', 'No Feedback')
            save_interaction(
                user_input=summary['content'],
                bot_response=summary['summary'],
                feedback=feedback,
                model_used='MBart',
                summary=summary['summary']
            )
        return redirect(url_for('index'))
    else:
        summaries = session.get('summaries', [])
        return render_template('feedback_collect.html', summaries=summaries)



#Analisi PDF 2.0 Cuda

@app.route('/upload-pdf', methods=['GET', 'POST'])
def upload_pdf():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or not file.filename.endswith('.pdf'):
            return render_template('index.html', error="File PDF non valido.")

        save_path = os.path.join('training_data', 'PDF', file.filename)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        file.save(save_path)

        try:
            # Estrai testo
            full_text = extract_text_from_pdf(save_path)
            if not full_text.strip():
                return render_template('index.html', error="Il PDF non contiene testo estraibile.")

            # Riassunto
            summary = summarize_text(full_text)

            # Salva nel DB
            new_doc = Document(
                filename=file.filename,
                full_text=full_text,
                summary=summary
            )
            db.session.add(new_doc)
            db.session.commit()

            return render_template('index.html', output=summary, user_input=full_text[:400] + '...', summary=summary)

        except Exception as e:
            return render_template('index.html', error=f"Errore durante l'elaborazione: {str(e)}")

    return render_template('upload_pdf.html',
                           filename=file.filename,
                           full_text=full_text,
                           summary=summary
                           )


@app.route('/documenti')
def documenti():
    docs = Document.query.order_by(Document.created_at.desc()).all()
    return render_template('documenti.html', docs=docs)





###########################TELEGRAM BOT

import sys
import telepot
from telepot.loop import MessageLoop
import os
from pypdf import PdfReader
from datetime import datetime


# === FLASK SETUP (già presente nel tuo file)
def run_flask():
    print("[FLASK] Avvio del server web Flask...")
    app.run(debug=True, port=5000, use_reloader=False)


# === TELEGRAM BOT (telepot)
# Estensione della classe TelegramBot con GPT e Wikipedia
# Estensione della classe TelegramBot con GPT e Wikipedia + LOG + Salvataggio su DB + feedback console
import logging



from datetime import datetime

class TelegramBot:
    def __init__(self):
        self.bot = None
        self.token = None
        self.registered_users = {}
        self.user_modes = {}  # user_id: "gpt" o "wikipedia"

        # Configura logging su file
        logging.basicConfig(
            filename='telegram_bot.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def save_interaction(self, user_input, bot_response, feedback, model_used, summary='', config_details='', generation_time=0.0):
        interaction = Interaction(
            user_input=user_input,
            bot_response=bot_response,
            feedback=feedback,
            model_used=model_used,
            additional_info=summary,
            config_details=config_details,
            generation_time=generation_time,
            created_at=datetime.utcnow()
        )
        db.session.add(interaction)
        db.session.commit()

        count = Interaction.query.count()
        print(f"[DB] Interazione salvata. Totale: {count}")
        logging.info(f"[DB] Interazione salvata per modello {model_used} - totale record: {count}")

    def handle_message(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        user_id = msg["from"]["id"]
        username = msg["from"].get("username", "Sconosciuto")

        logging.info(f"Messaggio da {username} ({user_id}) | Tipo: {content_type}")
        print(f"[MSG] da {username} ({user_id}) | Tipo: {content_type}")

        if content_type == 'text':
            text = msg['text'].strip()
            logging.info(f"Testo ricevuto: {text}")
            print(f"[TESTO] Ricevuto: {text}")

            # Comandi
            if text.lower() == '/start':
                self.registered_users[user_id] = username
                self.bot.sendMessage(chat_id, "🦁 Benvenuto nella Savana!")
                self.bot.sendMessage(chat_id,
                                     " 🦑 Scegli Modalità:\n"
                                     "/gpt - Attiva generatore di testo\n"
                                     "/wikipedia - Attiva modalità Wikipedia\n"
                                     "/testo_libero - Attiva Testo Libero \n"
                                     "/analisi_pdf_enciclopedia - Analisi PDF Input e Risposte Intelligenti(in progress)\n "
                                     "/help - Mostra questo messaggio"
                                     )
                print("[COMANDO] Start gestito, utente registrato.")

            elif text.lower() == '/gpt':
                self.user_modes[user_id] = "gpt"
                self.bot.sendMessage(chat_id, "🧠 Modalità GPT attiva.\nScrivimi qualcosa da generare.")
                print("[COMANDO] Modalità GPT attiva.")

            elif text.lower() == '/wikipedia':
                self.user_modes[user_id] = "wikipedia"
                self.bot.sendMessage(chat_id, "📚 Modalità Wikipedia attiva.\nScrivimi un argomento da cercare.")
                print("[COMANDO] Modalità Wikipedia attiva.")

            elif text.lower() == '/testo_libero':
                self.user_modes[user_id] = "testo_libero"
                self.bot.sendMessage(chat_id, "✂🦑 Modalità Testo Libero attiva.\nScrivimi un testo.")
                print("[COMANDO] Modalità testo_libero attiva.")



            elif text.lower() == '/analisi_pdf_enciclopedia':
                self.user_modes[user_id] = "analisi_pdf_enciclopedia"
                self.bot.sendMessage(chat_id,"📚 Modalità *Enciclopedia PDF* attivata.\n📄 Inviami ora un file PDF da analizzare.")


            elif text == '/help':
                self.bot.sendMessage(chat_id,
                                     "🆘 Comandi disponibili:\n"
                                     "/start - Riavvia il bot\n"
                                     "/analisi_pdf_enciclopedia - Analisi PDF Training Enciclopedia \n"
                                     "/gpt - Attiva generatore di testo\n"
                                     "/wikipedia - Attiva modalità Wikipedia\n"
                                     "/testo_libero - Attiva Testo Libero \n"
                                     "/help - Mostra questo messaggio"
                                     )

            else:
                mode = self.user_modes.get(user_id)
                if mode == "gpt":
                    print("[GPT] Avvio generazione...")
                    config = load_config("medium")
                    start_time = time.time()
                    response = generator(text, truncation=config['truncation'], max_length=config['max_length'],
                                         temperature=config['temperature'], top_p=0.9,
                                         num_return_sequences=config['num_return_sequences'],
                                         max_new_tokens=config.get('max_new_token', 50))[0]['generated_text']
                    generation_time = time.time() - start_time
                    print(f"[GPT] Testo generato: {response}")
                    self.bot.sendMessage(chat_id, response)
                    self.save_interaction(user_input=text, bot_response=response, feedback="from_telegram", model_used="GPT", generation_time=generation_time)
                    self.bot.sendMessage("@IntelligenzaArtificialeITA", f"[Riassunto] {response}")
                    self.bot.sendMessage(chat_id, "/start - Riavvia il bot\n")
                    logging.info(f"[GPT] Risposta inviata e salvata per {user_id}")

                elif mode == "wikipedia":
                    print("[Wikipedia] Avvio ricerca...")
                    content = fetch_wiki_summaries(text)
                    print(f"[Wikipedia] Contenuto estratto: {content}")
                    if not content:
                        self.bot.sendMessage(chat_id, "Nessun contenuto trovato su Wikipedia.")
                        logging.warning(f"[Wikipedia] Nessun contenuto per {text}")
                    else:
                        # Invia prima il contenuto intero
                        self.bot.sendMessage(chat_id, f"📄 Contenuto Wikipedia:\n\n{content}")
                        self.bot.sendMessage("@IntelligenzaArtificialeITA", f"[Wikipedia] Contenuto Wikipedia: {content}")

                        summary = summarize_text(content)
                        print(f"[Wikipedia] Contenuto AI: {summary}")
                        self.bot.sendMessage(chat_id, f"[Wikipedia] Contenuto AI: {summary}")
                        self.save_interaction(user_input=content, bot_response=summary, feedback="from_telegram", model_used="MBart", summary=summary)
                        self.bot.sendMessage("@IntelligenzaArtificialeITA", f"[Wikipedia] Contenuto AI: {summary}")
                        self.bot.sendMessage(chat_id, "/start - Riavvia il bot\n")
                        logging.info(f"[Wikipedia] Risposta inviata e salvata per {user_id}")

                elif mode == "testo_libero":
                    print("[MBART] Modalità Testo libero attiva...scrivi o incolla qel che vuoi.(max 1024 caratteri), 35 meglio XD")
                    content = text
                    summary = summarize_text(content)
                    print(f"[MBART] Riassunto: {summary}")
                    self.bot.sendMessage(chat_id, f"🧾 Riassunto:\n\n{summary}")
                    self.save_interaction(user_input=content, bot_response=summary, feedback="from_telegram",
                                          model_used="MBart", summary=summary)
                    self.bot.sendMessage("@IntelligenzaArtificialeITA", f"[Riassunto] {summary}")
                    self.bot.sendMessage(chat_id, "/start - Riavvia il bot\n")

                else:
                    logging.warning(f"[MODE] Nessuna modalità attiva per {user_id}")
                    print(f"[ERRORE] Nessuna modalità attiva per utente {user_id}")

        elif content_type == 'photo':
            self.bot.sendMessage(chat_id, "📷 Hai inviato una foto!")
            logging.info(f"[PHOTO] Ricevuta foto da {user_id}")
            print(f"[PHOTO] Ricevuta da {user_id}")

        elif content_type == 'document':
            mode = self.user_modes.get(user_id)
            if mode != "analisi_pdf_enciclopedia":
                self.bot.sendMessage(chat_id, "⚠️ Prima invia /analisi_pdf_enciclopedia")
                return

            file_id = msg['document']['file_id']
            original_name = msg['document'].get('file_name', 'documento.pdf')
            timestamp = int(time.time())
            file_name = f"{timestamp}_{original_name}"
            file_info = self.bot.getFile(file_id)
            file_url = f"https://api.telegram.org/file/bot{self.token}/{file_info['file_path']}"
            local_path = os.path.join('training_data', 'Telegram', file_name)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            try:
                with open(local_path, 'wb') as f:
                    f.write(requests.get(file_url).content)
                print(f"[PDF] File salvato in {local_path}")

                start_time = time.time()

                blocchi = extract_text_from_pdf_blocchi(local_path)
                if not blocchi:
                    self.bot.sendMessage(chat_id, "⚠️ Il PDF non contiene testo estraibile.")
                    return

                self.bot.sendMessage(chat_id, f"📚 Trovati {len(blocchi)} blocchi da 20 pagine. Inizio analisi...")

                riassunti_blocchi = []
                for i, blocco in enumerate(blocchi):
                    self.bot.sendMessage(chat_id, f"🧠 Analisi blocco {i + 1}/{len(blocchi)}...")
                    riassunto = summarize_text(blocco)
                    riassunti_blocchi.append(f"[Blocco {i + 1}]\n{riassunto}")

                final_summary = "\n\n".join(riassunti_blocchi)
                full_text = ' '.join(blocchi)
                keywords = ', '.join(sorted(set(w for w in full_text.lower().split() if len(w) > 5))[:10])

                # Blocchi salvati come testo unico
                block_texts = "\n\n".join([f"[Blocco {i + 1}]\n{blocchi[i]}" for i in range(len(blocchi))])
                block_summaries = "\n\n".join(riassunti_blocchi)

                elapsed = round(time.time() - start_time, 2)

                # ✅ Salvataggio nel DB
                new_doc = Document(
                    filename=file_name,
                    full_text=full_text,
                    summary=final_summary,
                    block_texts=block_texts,
                    block_summaries=block_summaries,
                    keywords=keywords,
                    num_blocks=len(blocchi),
                    processing_time=elapsed
                )



                # Genera nome file univoco
                unique_id = int(time.time())
                unique_file_name = f"{unique_id}_{file_name}"

                # ✅ Salvataggio locale su JSON
                json_path = os.path.join("training_data", "Telegram", f"{unique_file_name}.json")
                os.makedirs(os.path.dirname(json_path), exist_ok=True)

                json_data = {
                    "filename": unique_file_name,
                    "processing_time": elapsed,
                    "keywords": keywords,
                    "num_blocks": len(blocchi),
                    "block_texts": block_texts,
                    "block_summaries": block_summaries,
                    "full_text": full_text,
                    "final_summary": final_summary
                }

                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)

                # 🔁 Invia conferma su Telegram
                self.bot.sendMessage(chat_id, f"💾 Documento salvato come file JSON:")
                self.bot.sendMessage(chat_id, f"📁 {json_path}")

                # 📤 Risposte su Telegram
                self.bot.sendMessage(chat_id, f"✅ PDF completato: {file_name}")
                self.bot.sendMessage(chat_id, f"📄 Prime 300 parole:\n\n{' '.join(full_text.split()[:300])}")
                self.bot.sendMessage(chat_id, f"🧠 Riassunto finale (lunghezza: {len(final_summary)} caratteri):")

                for i in range(0, len(final_summary), 1000):
                    self.bot.sendMessage(chat_id, final_summary[i:i+1000])

                self.bot.sendMessage(chat_id, f"🏷️ Tag stimati: {keywords}")
                self.bot.sendMessage(chat_id, f"📦 Documento salvato su DB (ID: {new_doc.id}, blocchi: {len(blocchi)})")
                self.bot.sendMessage(chat_id, f"⏱️ Tempo totale: {elapsed} secondi")
                self.bot.sendMessage(chat_id,"/start - Riavvia il bot\n")

            except Exception as e:
                self.bot.sendMessage(chat_id, f"❌ Errore durante l'elaborazione:\n{str(e)}")


    def run_loop(self):
        def loop():
            print("[LOOP] Avvio polling diretto blindato...")
            offset = None
            while True:
                try:
                    updates = self.bot.getUpdates(offset=offset, timeout=30)
                    for update in updates:
                        offset = update['update_id'] + 1

                        if 'message' in update or 'channel_post' in update:
                            msg = update.get('message') or update.get('channel_post')
                            self.handle_message(msg)

                        elif 'my_chat_member' in update:
                            print("[INFO] Ignorato my_chat_member (cambio ruolo bot)")

                        else:
                            print(f"[INFO] Update ignorato: {list(update.keys())}")

                    time.sleep(1)
                except Exception as e:
                    print(f"[ERRORE] nel loop polling: {e}")
                    time.sleep(2)

        threading.Thread(target=loop, daemon=True).start()

    def run(self, token):
        self.token = token
        self.bot = telepot.Bot(token)
        self.run_loop()
        print("🤖 Bot in ascolto (modalità polling manuale)...")
        logging.info("Bot Telegram avviato e in ascolto...")
        while True:
            time.sleep(5)


# === AVVIO PRINCIPALE
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("❌ Specifica 'flask' o 'telegram' come argomento.")
        sys.exit(1)

    mode = sys.argv[1].lower()

    if mode == "flask":
        run_flask()

    elif mode == "telegram":
        bot_token = "7638639600:AAHl65R20LxFXDaRmeuPBKO_0aSowrNzRyo"
        telegram_bot = TelegramBot()
        telegram_bot.run(bot_token)

    else:
        print("❌ Argomento non valido. Usa 'flask' o 'telegram'.")