from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/packages")
def packages():
    return render_template("packages.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/buy/<box_type>")
def buy(box_type):
    return render_template("buy.html", box_type=box_type)

if __name__ == "__main__":
    app.run(debug=True)
