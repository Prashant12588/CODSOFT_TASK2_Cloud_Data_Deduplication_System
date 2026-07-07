from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return """
    <h1>Cloud Data Deduplication System</h1>
    <p>Project is running successfully.</p>
    """

if __name__ == "__main__":
    app.run(debug=True)
