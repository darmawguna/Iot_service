import logging
import json
import threading
import time
import paho.mqtt.client as mqtt
import requests
import redis
import sys
import signal

# --- Konfigurasi Awal ---
sys.path.append('.') # Menambahkan direktori root proyek ke path
try:
    from config.settings import Config
    from influxdb.influxdb_helper import write_data
except ImportError as e:
    print(f"Error: Gagal mengimpor modul. Pastikan Anda menjalankan skrip dari direktori root. {e}")
    sys.exit(1)

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')
logger = logging.getLogger("MQTTWorker")

# --- Channel Redis ---
COMMAND_CHANNEL = "command_to_mqtt"    # Channel untuk menerima perintah dari web_server
DATA_CHANNEL = "data_for_dashboard" # Channel untuk mengirim data ke web_server

class MQTTWorker:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # --- State ---
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.client.reconnect_delay_set(min_delay=1, max_delay=120)
        
        self.is_running = False
        self.whitelist_cache = set()
        self.refresh_thread = None
        
        # --- Koneksi ke Redis ---
        try:
            self.redis_client = redis.Redis(
                host=Config.REDIS_HOST,
                port=Config.REDIS_PORT,
                db=0,
                decode_responses=True # Otomatis decode
            )
            self.redis_client.ping()
            self.logger.info("✅ (MQTT Worker) Berhasil terhubung ke Redis.")
        except Exception as e:
            self.logger.error(f"❌ (MQTT Worker) Gagal terhubung ke Redis: {e}")
            sys.exit(1)
            
    # --- Callbacks MQTT ---
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.logger.info("✅ (MQTT) Berhasil terhubung ke Broker!")
            client.subscribe([
                (Config.MQTT_TOPIC_WATERLEVEL, 0),
                (Config.MQTT_TOPIC_STATUS, 1),
                (Config.REGISTRATION_RESPONSE_TOPIC, 0) # Tetap subscribe untuk update whitelist
            ])
            self.logger.info(f"👂 (MQTT) Berlangganan ke topik data.")
        else:
            self.logger.error(f"❌ (MQTT) Gagal terhubung, kode: {rc}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            device_id = payload.get("device_id") or payload.get("sensor_id")

            # --- Logika untuk Respons Registrasi ---
            if msg.topic == Config.REGISTRATION_RESPONSE_TOPIC:
                if payload.get("status") == "success" and device_id:
                    self.whitelist_cache.add(device_id)
                    self.logger.info(f"✅ (Whitelist) Perangkat {device_id} berhasil terdaftar via MQTT.")
                else:
                    self.logger.warning(f"Registrasi MQTT gagal: {payload.get('message')}")
                return

            # --- Logika untuk Data Sensor ---
            if not device_id:
                self.logger.warning("❌ Payload tidak ada device_id. Diabaikan.")
                return

            if device_id not in self.whitelist_cache:
                self.logger.warning(f"⛔ Perangkat tidak sah: {device_id}. Pesan ditolak.")
                return

            if msg.topic == Config.MQTT_TOPIC_WATERLEVEL:
                # 1. Tulis ke InfluxDB
                write_data(payload)
                # 2. Teruskan data ke Dashboard (via Redis)
                self.redis_client.publish(DATA_CHANNEL, json.dumps(payload))
                self.logger.info(f"Menerima data dari {device_id} dan meneruskannya ke dashboard.")
                try:
                    # Ambil data spesifik untuk heartbeat
                    heartbeat_data = {
                        "fw_version": payload.get("fw_version"),
                        "rssi": payload.get("rssi")
                    }
                    
                    #TODO Pastikan URL Laravel benar (bisa ditaruh di Config)
                    laravel_url = f"http://localhost:8000/api/iot/{device_id}/heartbeat"
                    
                    # Kirim request (timeout kecil agar tidak memblokir lama)
                    requests.post(laravel_url, json=heartbeat_data, timeout=2)
                    
                except Exception as req_err:
                    self.logger.error(f"Gagal update heartbeat ke Laravel: {req_err}")

                self.logger.info(f"Data diproses untuk {device_id} (Ver: {payload.get('fw_version')})")

        except Exception as e:
            self.logger.error(f"❌ Error memproses pesan MQTT: {e}", exc_info=True)

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            self.logger.warning(f"🔌 (MQTT) Koneksi terputus (Code: {rc}). Mencoba terhubung kembali...")

    # --- Logika Whitelist (Tidak berubah) ---
    def load_whitelist_from_backend(self):
        backend_url = Config.WHITELIST_API_URL 
        try:
            self.logger.info("⏳ Memuat whitelist dari backend...")
            response = requests.get(backend_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.whitelist_cache = set(data.get("device_ids", []))
                self.logger.info(f"✅ Whitelist dimuat. Total perangkat: {len(self.whitelist_cache)}")
            else:
                self.logger.error(f"❌ Gagal memuat whitelist. Status: {response.status_code}")
        except requests.RequestException as e:
            self.logger.error(f"❌ Error saat memuat whitelist: {e}")

    def _periodic_whitelist_refresh_loop(self):
        self.logger.info("Thread background refresh whitelist dimulai.")
        while self.is_running:
            self.load_whitelist_from_backend()
            time.sleep(3600) # Refresh setiap 1 jam
        self.logger.info("Thread background refresh whitelist berhenti.")

    # --- Listener Redis (Logika Inti Baru) ---
    def _redis_listener_loop(self):
        """
        Mendengarkan perintah dari Web Server (via Redis) dan
        meneruskannya ke perangkat (via MQTT).
        """
        self.logger.info("Memulai listener Redis Pub/Sub untuk perintah...")
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe(COMMAND_CHANNEL) # Channel perintah dari Flask
        
        for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    self.logger.info(f"Menerima perintah dari Redis: {data.get('type')}")
                    
                    if data['type'] == 'register_device':
                        self._handle_mqtt_publish(data['topic'], data['payload'])
                    
                    elif data['type'] == 'command':
                        # Validasi whitelist sebelum mengirim perintah
                        if data['device_id'] in self.whitelist_cache:
                            self._handle_mqtt_publish(data['topic'], data['payload'])
                        else:
                            self.logger.warning(f"Perintah ditolak: {data['device_id']} tidak ada di whitelist.")
                            
                except Exception as e:
                    self.logger.error(f"Error memproses pesan dari Redis: {e}")

    def _handle_mqtt_publish(self, topic, payload):
        """Fungsi internal untuk mempublikasikan ke MQTT."""
        if not self.is_running or not self.client.is_connected():
            self.logger.error("MQTT client tidak terhubung. Perintah dibatalkan.")
            return
            
        self.client.publish(topic, json.dumps(payload))
        self.logger.info(f"📡 (MQTT) Perintah dipublikasikan ke topik: {topic}")
                    
    # --- Kontrol Service ---
    def start(self):
        if self.is_running:
            return
        
        logger.info("🚀 Memulai MQTT Worker...")
        self.load_whitelist_from_backend() # Muat whitelist saat start
        
        try:
            self.client.connect(Config.MQTT_BROKER, Config.MQTT_PORT, 60)
        except Exception as e:
            self.logger.error(f"FATAL: Gagal terhubung ke MQTT Broker saat start: {e}")
            sys.exit(1)
            
        self.client.loop_start() 
        self.is_running = True

        # Mulai semua thread background
        threading.Thread(target=self._periodic_whitelist_refresh_loop, daemon=True).start()
        threading.Thread(target=self._redis_listener_loop, daemon=True).start()
        
        logger.info("✅ MQTT Worker berjalan.")

    def stop(self):
        logger.info("🛑 Menghentikan MQTT Worker...")
        self.is_running = False
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("MQTT Worker berhenti.")

# --- Main ---
if __name__ == "__main__":
    worker = MQTTWorker()
    
    def signal_handler(sig, frame):
        logger.info("\n🛑 Sinyal shutdown diterima.")
        worker.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    worker.start()
    
    # Jaga agar script utama tetap berjalan
    while True:
        time.sleep(1)