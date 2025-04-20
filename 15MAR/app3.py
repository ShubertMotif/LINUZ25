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



#MODEL TRASFORMER

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


def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ''
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:  # Assicurati che il testo non sia None
            text += page_text + ' '
    return text


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

tokenizerBERT = BertTokenizer.from_pretrained('dbmdz/bert-base-italian-uncased')
modelBERT = BertForSequenceClassification.from_pretrained('dbmdz/bert-base-italian-uncased')




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

from transformers import MBartForConditionalGeneration, MBart50TokenizerFast

modelMBART = MBartForConditionalGeneration.from_pretrained("facebook/mbart-large-50-many-to-many-mmt")
tokenizerMBART = MBart50TokenizerFast.from_pretrained("facebook/mbart-large-50-many-to-many-mmt")


def summarize_text(text):
    print("[MBART] Avvio riassunto...")

    # Mostra il testo originale (troncato per non riempire il terminale)
    print(f"[MBART] Testo ricevuto ({len(text)} caratteri): {text[:200]}{'...' if len(text) > 200 else ''}")

    # Assicura la lunghezza gestibile per il modello
    if len(text) > 1024:
        text = text[:1024]
        print("[MBART] Testo troncato a 1024 caratteri.")

    # Imposta lingua per tokenizer
    tokenizerMBART.src_lang = "it_IT"

    # Prepara input per il modello
    inputs = tokenizerMBART(text, return_tensors="pt", padding=True, truncation=True, max_length=1024)

    # Genera il riassunto
    summary_ids = modelMBART.generate(
        inputs['input_ids'],
        forced_bos_token_id=tokenizerMBART.lang_code_to_id["it_IT"],
        num_beams=5,
        length_penalty=1.0,
        max_length=350,
        min_length=50,
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

        print('SUMMARY', summary)
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





###########################TELEGRAM BOT

import sys
import telepot
from telepot.loop import MessageLoop

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
                self.bot.sendMessage(chat_id, "Scrivi /gpt o /wikipedia per scegliere la modalità.")
                print("[COMANDO] Utente registrato e /start gestito.")

            elif text.lower() == '/gpt':
                self.user_modes[user_id] = "gpt"
                self.bot.sendMessage(chat_id, "Modalità GPT attiva. Scrivi qualcosa da generare!")
                print("[COMANDO] Modalità GPT attiva.")

            elif text.lower() == '/wikipedia':
                self.user_modes[user_id] = "wikipedia"
                self.bot.sendMessage(chat_id, "Modalità Wikipedia attiva. Scrivi un argomento!")
                print("[COMANDO] Modalità Wikipedia attiva.")

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

                        summary = summarize_text(content)
                        print(f"[Wikipedia] Riassunto: {summary}")
                        self.bot.sendMessage(chat_id, summary)
                        self.save_interaction(user_input=content, bot_response=summary, feedback="from_telegram", model_used="MBart", summary=summary)
                        logging.info(f"[Wikipedia] Risposta inviata e salvata per {user_id}")
                else:
                    self.bot.sendMessage(chat_id, "❗ Prima scegli una modalità con /gpt o /wikipedia")
                    logging.warning(f"[MODE] Nessuna modalità attiva per {user_id}")
                    print(f"[ERRORE] Nessuna modalità attiva per utente {user_id}")

        elif content_type == 'photo':
            self.bot.sendMessage(chat_id, "📷 Hai inviato una foto!")
            logging.info(f"[PHOTO] Ricevuta foto da {user_id}")
            print(f"[PHOTO] Ricevuta da {user_id}")

    def run(self, token):
        self.bot = telepot.Bot(token)
        MessageLoop(self.bot, self.handle_message).run_as_thread()
        print("🤖 Bot in ascolto...")
        logging.info("Bot Telegram avviato e in ascolto...")
        while True:
            pass





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


