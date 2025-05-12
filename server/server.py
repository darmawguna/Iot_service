from flask import Flask
from api.routes import api
from api.waterlevel.endpoints import waterlevel
from api.iot.endpoints import iotdevice

app = Flask(__name__)
app.register_blueprint(api, urlprefix="/api/iot")
app.register_blueprint(waterlevel, url_prefix="/api/waterlevel")
app.register_blueprint(iotdevice, url_prefix="/api/iot")

def run_server():
    """Menjalankan server Flask."""
    app.run(debug=False, host="0.0.0.0", port=5000)

# print(app.url_map)