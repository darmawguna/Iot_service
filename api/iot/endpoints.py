import redis
import json
import logging
from flask import Blueprint, jsonify, request
from config.settings import Config  # Pastikan file config.py/settings.py Anda memiliki REDIS_HOST dan REDIS_PORT
from helper.form_validation import get_form_data
from helper.json_formatter import create_response

# --- Setup ---
iotdevice = Blueprint("iotdevice", __name__)
logger = logging.getLogger(__name__)

# Channel Redis yang akan kita gunakan
COMMAND_CHANNEL = "command_to_mqtt" 
# --- Koneksi ke Redis ---
try:
    # Buat koneksi Redis di level modul
    redis_client = redis.Redis(
        host=Config.REDIS_HOST,
        port=Config.REDIS_PORT,
        db=0,
        decode_responses=True # Otomatis decode dari bytes ke string
    )
    redis_client.ping()
    logger.info("✅ (API Endpoints) Berhasil terhubung ke Redis.")
except Exception as e:
    logger.error(f"❌ (API Endpoints) Gagal terhubung ke Redis: {e}")
    redis_client = None

# --- Endpoint yang Telah Di-refactor ---

@iotdevice.route("/threshold", methods=["POST"])
def set_threshold_iotdevice():
    """
    Menerima perintah 'set threshold' dan meneruskannya ke
    MQTT Worker melalui Redis secara asinkron.
    """
    if not redis_client:
        return create_response(status=False, message="Koneksi ke service internal (Redis) gagal"), 503

    try:
        required = get_form_data(["sensor_id", "warning_level", "danger_level", "sensor_height"]) 
        sensor_id = required["sensor_id"]
        
        # Buat payload yang akan dikonsumsi oleh perangkat
        payload = {
            "warning_level": required["warning_level"],
            "danger_level": required["danger_level"],
            "sensor_height": required["sensor_height"],
            "sensor_id": sensor_id
        }
        
        # Buat pesan lengkap untuk MQTT Worker
        message = {
            "type": "command", # Tipe perintah generik
            "device_id": sensor_id,
            "topic": f"{Config.MQTT_BASE_TOPIC_COMMAND}/{sensor_id}", # Tentukan topik di sini
            "payload": payload
        }
        
        # Publikasikan ke Redis
        redis_client.publish(COMMAND_CHANNEL, json.dumps(message))
        
        # Berikan respons cepat ke klien (Laravel)
        return create_response(
            data=payload,
            message="Perintah 'set threshold' telah diterima dan sedang diproses",
            status_code=202 # 202 Accepted (Diterima, belum dieksekusi)
        )
    except Exception as e:
        return create_response(status=False, message=str(e)), 500
    

@iotdevice.route("/register-device", methods=["POST"])
def register_device():
    """
    Menerima perintah 'register device' dari Laravel dan meneruskannya
    ke MQTT Worker melalui Redis secara asinkron.
    """
    if not redis_client:
        return create_response(status=False, message="Koneksi ke service internal (Redis) gagal"), 503

    try:
        required = get_form_data(["device_id", "device_token", "warning_level", "danger_level", "sensor_height"]) 
        device_id = required["device_id"]
    
        payload = {
            "device_id": device_id,
            "device_token": required["device_token"],
            "warning_level": required["warning_level"],
            "danger_level": required["danger_level"],
            "sensor_height": required["sensor_height"],
        }

        # Buat pesan lengkap untuk MQTT Worker
        message = {
            "type": "register_device", # Tipe perintah khusus
            "device_id": device_id,
            "topic": Config.REGISTRATION_REQUEST_TOPIC, # Tentukan topik
            "payload": payload
        }

        # Publikasikan ke Redis
        redis_client.publish(COMMAND_CHANNEL, json.dumps(message))

        # --- RESPON BARU ---
        # Langsung beri tahu Laravel bahwa perintah sudah diterima
        return create_response(
            data=payload,
            message="Perintah registrasi telah diterima dan sedang diproses",
            status_code=202 # 202 Accepted
        )

    except Exception as e:
        return create_response(status=False, message=str(e)), 500

@iotdevice.route('/<device_id>/change-status', methods=['PATCH'])
def change_status(device_id):
    # Endpoint ini sebenarnya bisa digunakan untuk SEMUA command (bukan cuma status)
    data = request.json # Laravel mengirim {"cmd": "OTA_UPDATE", "url": "..."}
    
    if not redis_client:
         return create_response(status=False, message="Redis error"), 503

    try:
        redis_client.publish('command_to_mqtt', json.dumps({
            "type": "command", 
            "device_id": device_id,
            "topic": f"{Config.MQTT_BASE_TOPIC_COMMAND}/{device_id}", 
            "payload": data 
        }))
        return jsonify({"status": "success", "message": "Command queued"}), 202
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500