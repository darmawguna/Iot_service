from flask import Flask
from api.routes import api

app = Flask(__name__)
app.register_blueprint(api)

def run_server():
    """Menjalankan server Flask."""
    app.run(debug=True, host="0.0.0.0", port=5000)
