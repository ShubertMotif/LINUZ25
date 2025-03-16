from flask import Flask, render_template, request
from transformers import GPT2Tokenizer, GPT2LMHeadModel, Trainer, TrainingArguments
import requests
from bs4 import BeautifulSoup
import time
from datasets import load_dataset

app = Flask(__name__)

# Carica il tokenizer e il modello GPT-2 Medium preaddestrato
tokenizer = GPT2Tokenizer.from_pretrained('gpt2-medium')
model = GPT2LMHeadModel.from_pretrained('gpt2-medium')

def encode(examples):
    return tokenizer(examples['text'], truncation=True, padding='max_length', max_length=512)

# Carica il dataset (ipoteticamente pre-caricato e processato)
dataset = load_dataset('text', data_files={'train': ['path/to/dataset.txt']})
dataset = dataset.map(encode, batched=True)
dataset.set_format(type='torch', columns=['input_ids'])

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'user_input' in request.form:
            # Logica per il download e la generazione del testo da Wikipedia
            user_input = request.form['user_input']
            response = requests.get(f"https://it.wikipedia.org/wiki/{user_input}")
            soup = BeautifulSoup(response.content, 'html.parser')
            text = ' '.join(p.text for p in soup.find_all('p'))

            inputs = tokenizer(text, return_tensors='pt', truncation=True, max_length=512)
            outputs = model.generate(inputs['input_ids'], max_new_tokens=500, num_return_sequences=1)
            generation_time = time.time() - start_time
            response = tokenizer.decode(outputs[0], skip_special_tokens=True)
            return render_template('index.html', output=response, time=generation_time)
        elif 'file_input' in request.files:
            # Logica per il processing di un file selezionato
            file = request.files['file_input']
            text = file.read().decode('utf-8')
            inputs = tokenizer(text, return_tensors='pt', truncation=True, max_length=512)
            outputs = model.generate(inputs['input_ids'], max_new_tokens=500, num_return_sequences=1)
            response = tokenizer.decode(outputs[0], skip_special_tokens=True)
            return render_template('index.html', output=response)

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
