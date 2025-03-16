from flask import Flask, render_template, request
import requests

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        user_input = request.form['user_input']
        max_length = request.form['max_length']
        temperature = request.form['temperature']
        data = {'text': user_input, 'max_length': max_length, 'temperature': temperature}
        response = requests.post('http://localhost:5001/generate', json=data)
        return render_template('index.html', output=response.json(), user_input=user_input, max_length=max_length, temperature=temperature)

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
