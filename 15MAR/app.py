from flask import Flask, render_template, request
from transformers import GPT2Tokenizer, GPT2LMHeadModel
import requests
from bs4 import BeautifulSoup
import time

app = Flask(__name__)

# Carica il tokenizer e il modello GPT-2 Medium preaddestrato
tokenizer = GPT2Tokenizer.from_pretrained('gpt2-medium')
model = GPT2LMHeadModel.from_pretrained('gpt2-medium')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Scarica e prepara il contenuto di Wikipedia
        user_input = request.form['user_input']
        response = requests.get(f"https://it.wikipedia.org/wiki/{user_input}")
        soup = BeautifulSoup(response.content, 'html.parser')
        text = ' '.join(p.text for p in soup.find_all('p'))  # Estrae il testo dai paragrafi

        # Processa l'input con il modello
        start_time = time.time()
        inputs = tokenizer(text, return_tensors='pt', truncation=True,
                           max_length=512)  # Codifica l'input con limitazione
        outputs = model.generate(inputs['input_ids'], max_new_tokens=500,
                                 num_return_sequences=1)  # Genera fino a 500 nuovi token
        generation_time = time.time() - start_time
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Restituisce la risposta generata e il tempo di elaborazione
        return render_template('index.html', user_input=user_input, output=response, time=generation_time)
    return render_template('index.html', user_input='', output='', time=0)

if __name__ == '__main__':
    app.run(debug=True)
