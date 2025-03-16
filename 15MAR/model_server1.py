from flask import Flask, request, render_template
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import requests
from bs4 import BeautifulSoup
import json

app = Flask(__name__)

# Carica il tokenizer e il modello
tokenizer = AutoTokenizer.from_pretrained("GroNLP/gpt2-medium-italian-embeddings")
model = AutoModelForCausalLM.from_pretrained("GroNLP/gpt2-medium-italian-embeddings")
generator = pipeline("text-generation", model=model, tokenizer=tokenizer)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        topic = request.form.get('user_input')
        response = fetch_wiki_summary(topic)
        return render_template('index.html', user_input=topic, output=response)
    return render_template('index.html')

def fetch_wiki_summary(topic):
    """Fetches content from Wikipedia and generates a summary."""
    url = f"https://it.wikipedia.org/wiki/{topic}"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    text = ' '.join(p.text for p in soup.find_all('p')[:5])  # Extract the first 5 paragraphs
    summary = generator(text, max_length=150, num_return_sequences=1)[0]['generated_text']
    return summary

if __name__ == '__main__':
    app.run(debug=True, port=5000)
