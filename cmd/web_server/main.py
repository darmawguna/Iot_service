import logging
import json
import threading
import redis
import sys

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, join_room
from flask_cors import CORS  # Pastikan untuk mengimpor CORS

# --- Konfigurasi Awal ---
# Impor file konfigurasi dan blueprint API Anda
# PENTING: Sesuaikan path impor ini berdasarkan struktur folder Anda
# Jika cmd/ berada di root, Anda mungkin perlu menambahkan root ke sys.path
sys.path.append('.') # Menambahkan direktori root proyek ke path
from config.settings import Config
from api.waterlevel.endpoints import waterlevel
from api.iot.endpoints import iotdevice

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Inisialisasi Aplikasi ---
app = Flask(__name__)
CORS(app) # Mengaktifkan CORS untuk semua rute
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# --- Koneksi ke Redis ---
try:
    redis_client = redis.Redis(
        host=Config.REDIS_HOST,
        port=Config.REDIS_PORT,
        db=0,
        decode_responses=True # Otomatis decode dari bytes ke string
    )
    redis_client.ping()
    logger.info("✅ (Web Server) Terhubung ke Redis.")
except Exception as e:
    logger.error(f"❌ (Web Server) Gagal terhubung ke Redis: {e}")
    sys.exit(1) # Keluar jika tidak bisa terhubung ke Redis

# --- Endpoint HTTP ---

# 1. Endpoint untuk Notifikasi Aduan dari Laravel
@app.route('/notify', methods=['POST'])
def handle_laravel_notification():
    """
    Menerima webhook dari Laravel (Aduan Masyarakat Baru) dan
    menyiarkannya ke dashboard admin yang terhubung.
    """
    try:
        data = request.json
        channel = data.get('channel')    # e.g., 'admin_notifications'
        event_name = data.get('event')     # e.g., 'new_report'
        payload = data.get('data')

        if not all([channel, event_name, payload]):
            logger.warning("Webhook /notify menerima payload tidak lengkap.")
            return jsonify({"status": "error", "message": "Payload tidak lengkap"}), 400

        logger.info(f"Meneruskan pesan dari Laravel ke WS channel '{channel}'")
        socketio.emit(event_name, payload, room=channel)
        
        return jsonify({"status": "sukses"}), 200

    except Exception as e:
        logger.error(f"Error menangani /notify webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# 2. Daftarkan Blueprint API Anda
# PENTING: Anda harus merefaktor kode di dalam blueprint ini!
app.register_blueprint(waterlevel, url_prefix="/api/waterlevel")
app.register_blueprint(iotdevice, url_prefix="/api/iot")

# --- Logika WebSocket (Socket.IO) ---
@socketio.on('connect')
def handle_connect():
    logger.info(f"🔌 (WebSocket) Client {request.sid} terhubung")

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"🔌 (WebSocket) Client {request.sid} terputus")

@socketio.on('join_admin_room')
def handle_join_admin_room(data=None):
    """
    Event untuk dashboard admin bergabung ke room notifikasi.
    """
    join_room('admin_notifications')
    logger.info(f"Client {request.sid} bergabung ke room: admin_notifications")

@socketio.on('command_to_device')
def handle_command_from_dashboard(data):
    """
    Menerima perintah dari dashboard (misal: OTA) dan
    meneruskannya ke MQTT Worker melalui Redis.
    """
    logger.info(f"Menerima perintah dari dashboard: {data}")
    try:
        # Publikasikan perintah ke channel yang akan didengarkan oleh mqtt_worker
        redis_client.publish('command_to_mqtt', json.dumps(data))
    except Exception as e:
        logger.error(f"Gagal mempublikasikan perintah ke Redis: {e}")

# --- Listener Redis (Berjalan di background thread) ---
def redis_listener_loop():
    """
    Mendengarkan data dari MQTT Worker (via Redis) dan
    menyiarkannya ke dashboard (via WebSocket).
    """
    logger.info("Memulai listener Redis Pub/Sub...")
    pubsub = redis_client.pubsub()
    pubsub.subscribe('data_for_dashboard') # Channel data dari MQTT
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                data = json.loads(message['data'])
                # Siarkan data (misal: water level) ke semua klien dashboard
                socketio.emit('water_level_update', data)
            except Exception as e:
                logger.error(f"Error memproses pesan dari Redis: {e}")

# --- Main ---
def run_web_server():
    logger.info("🚀 Memulai Web Server (Flask-SocketIO)...")
    
    # Mulai listener Redis di thread terpisah
    threading.Thread(target=redis_listener_loop, daemon=True).start()
    
    # Jalankan server
    # Gunakan Gunicorn di produksi, ini hanya untuk development
    socketio.run(app, debug=False, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)

if __name__ == "__main__":
    run_web_server()