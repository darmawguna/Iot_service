# File: helper/mqtt_helper.py (atau di mana pun Anda meletakkannya)

import json
import logging
import paho.mqtt.client as mqtt
import threading
import time
from queue import Queue
import requests
from config.settings import Config
from influxdb.influxdb_helper import write_data

# Setup logging di level modul
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

class MQTTHelper:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # --- State sekarang menjadi instance attributes, bukan global ---
        self.client = None
        self.is_running = False
        self.whitelist_cache = set()
        
        # Untuk mekanisme request/response
        self.response_queue = Queue()
        self.register_event = threading.Event()
        # --- PENAMBAHAN: Variabel untuk mengontrol thread refresh ---
        self.refresh_thread = None

    # --- Bagian Callbacks ---
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.logger.info("✅ MQTT Connected Successfully!")
            client.subscribe([
                (Config.MQTT_TOPIC_WATERLEVEL, 0),
                (Config.MQTT_TOPIC_STATUS, 1),
                (Config.REGISTRATION_RESPONSE_TOPIC, 0)
            ])
            self.logger.info(f"👂 Subscribed to topics.")
        else:
            self.logger.error(f"❌ MQTT Connection failed with code {rc}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            
            if msg.topic == Config.REGISTRATION_RESPONSE_TOPIC:
                self.logger.info(f"📥 Registration response received: {payload}")
                self.response_queue.put(payload)
                self.register_event.set()
                return

            device_id = payload.get("device_id") or payload.get("sensor_id")
            if not device_id:
                self.logger.warning("❌ Payload does not contain device_id. Ignored.")
                return

            if device_id not in self.whitelist_cache:
                self.logger.warning(f"⛔ Unauthorized device ID: {device_id}. Message rejected.")
                return

            if msg.topic == Config.MQTT_TOPIC_WATERLEVEL:
                # Disarankan untuk memanggil fungsi write_data di sini jika ini adalah 'jembatan'
                response = write_data(payload)
                if response is None:
                    self.logger.error("❌ Failed to write data to InfluxDB.") 
                else:
                    self.logger.info(f"✅ Data written to InfluxDB: {response}")

        except Exception as e:
            self.logger.error(f"❌ Error processing message: {e}", exc_info=True)

    def on_disconnect(self, client, userdata, rc):
        # PERBAIKAN: Jangan gunakan blocking loop di sini.
        # Paho-MQTT akan menangani reconnect secara otomatis.
        if rc != 0:
            self.logger.warning(f"🔌 Unexpected MQTT disconnection (Code: {rc}). Will attempt to reconnect automatically...")

    
    # --- Bagian Metode Kontrol ---
    def start(self):
        if self.is_running:
            self.logger.warning("⚠ MQTT Client is already running!")
            return

        self.logger.info("🚀 Starting MQTT Helper...")
        
        # Muat whitelist sebelum koneksi
        self.load_whitelist_from_backend()
        
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

        
        self.client.reconnect_delay_set(min_delay=1, max_delay=120)

        try:
            self.client.connect(Config.MQTT_BROKER, Config.MQTT_PORT, 60)
            self.client.loop_start() 
            self.is_running = True
            self.logger.info("✅ MQTT Client started and running in background.")
            # --- PERBAIKAN: Mulai thread refresh di sini ---
            if self.refresh_thread is None or not self.refresh_thread.is_alive():
                self.refresh_thread = threading.Thread(target=self._periodic_whitelist_refresh_loop, daemon=True)
                self.refresh_thread.start()
        except Exception as e:
            self.logger.error(f"❌ Could not connect to MQTT Broker on start: {e}")

    def stop(self):
        if not self.is_running:
            return
        
        self.logger.info("🛑 Stopping MQTT Helper...")
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
        self.is_running = False
        self.logger.info("MQTT Client stopped.")

    # --- Bagian Metode Fungsional ---
    def load_whitelist_from_backend(self):
        # PERBAIKAN: Gunakan URL dari Config
        backend_url = Config.WHITELIST_API_URL 
        try:
            self.logger.info("⏳ Requesting whitelist from backend...")
            response = requests.get(backend_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.whitelist_cache = set(data.get("device_ids", []))
                self.logger.info(f"✅ Whitelist loaded successfully. Total devices: {len(self.whitelist_cache)}")
            else:
                self.logger.error(f"❌ Failed to fetch whitelist. Status: {response.status_code}")
        except requests.RequestException as e:
            self.logger.error(f"❌ Error fetching whitelist: {e}")

    def publish_register_device(self, device_id: str, payload: dict, timeout=15):
        if not self.is_running or not self.client:
            raise ConnectionError("MQTT client is not running.")
        
        if device_id in self.whitelist_cache:
            self.logger.warning(f"Device {device_id} is already in whitelist cache.")
            return {"status": "ignored", "message": "Device already registered"}

        # Bersihkan event & queue sebelum request baru
        self.register_event.clear()
        while not self.response_queue.empty():
            self.response_queue.get()
            
        # Publish
        topic = Config.REGISTRATION_REQUEST_TOPIC
        self.client.publish(topic, json.dumps(payload))
        self.logger.info(f"📡 Published registration command for {device_id}")

        # Tunggu response
        if self.register_event.wait(timeout=timeout):
            response = self.response_queue.get()
            if response.get("device_id") == device_id:
                self.whitelist_cache.add(device_id)
                self.logger.info(f"✅ Registration successful for {device_id}")
                return response
        
        self.logger.error(f"⏰ Timeout waiting for registration response from {device_id}")
        return None
        # --- PERBAIKAN: Fungsi refresh sekarang berjalan dalam loop ---
    def _periodic_whitelist_refresh_loop(self):
        """Fungsi ini dimaksudkan untuk dijalankan di thread terpisah."""
        self.logger.info("Background whitelist refresh thread started.")
        while self.is_running:
            self.logger.info("🔄 Refreshing whitelist from background thread...")
            self.load_whitelist_from_backend()
            # Gunakan time.sleep() untuk interval
            time.sleep(3600) # Tunggu 1 jam
        self.logger.info("Background whitelist refresh thread stopped.")
    
    def publish_command(self, device_id: str, payload: dict):
        if not self.is_running or not self.client:
            raise ConnectionError("MQTT client is not running.")
        
        if device_id not in self.whitelist_cache:
            raise PermissionError(f"Device {device_id} is not whitelisted.")

        topic = f"{Config.MQTT_BASE_TOPIC_COMMAND}/{device_id}"
        self.client.publish(topic, json.dumps(payload))
        self.logger.info(f"📡 Command published to {device_id} on topic {topic}")


mqtt_helper = MQTTHelper()