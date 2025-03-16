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

class Interaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_input = db.Column(db.String(500), nullable=False)
    bot_response = db.Column(db.String(500), nullable=False)
    feedback = db.Column(db.String(100))



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



def save_interaction(user_input, bot_response, feedback=None):
    interaction = Interaction(user_input=user_input, bot_response=bot_response, feedback=feedback)
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
    user_input = request.form['user_input']
    response = request.form['response']
    feedback = request.form['feedback']
    save_interaction(user_input, response, feedback)
    return redirect('/thank_you')

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



if __name__ == '__main__':
    app.run(debug=True, port=5000)
