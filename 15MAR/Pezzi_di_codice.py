
@app.route('/XXXanalyze-wikipedia', methods=['GET', 'POST'])
def XXXanalyze_wikipedia():
    if request.method == 'POST':
        keyword = request.form.get('keyword')
        if not keyword:
            return render_template('index.html', error="Nessuna parola chiave fornita.")

        summary = fetch_wiki_summaries(keyword)
        print('ROUT ANALIZE WIKIPEDIA SUMMARY_>')
        print(summary)
        time.sleep(1)
        if len(summary) > 240:
            summary = summary[:240]  # Assicurati che la lunghezza non superi 90 parole

        config = load_config('medium')  # Puoi scegliere una configurazione appropriata
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