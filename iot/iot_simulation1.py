import paho.mqtt.client as mqtt
import json
import time
import random
import string
from datetime import datetime
import threading

# ====================== Konstanta MQTT ======================
MQTT_BROKER = "localhost"  # Ganti dengan alamat broker
MQTT_PORT = 1883
REGISTER_COMMAND_TOPIC = "iot/register-device/request"
REGISTER_RESPONSE_TOPIC = "iot/register-device/response"
WATERLEVEL_TOPIC = "iot/waterlevel"

# ====================== Simulasi Device ID ======================
def generate_random_device_id(prefix="SIM-"):
    return prefix + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

DEVICE_ID = ""  # Akan di-set setelah registrasi berhasil
print(f"📱 Simulated Device Booted with ID: {DEVICE_ID}")

# ====================== Callback Saat Terhubung ======================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ MQTT Connected")
        client.subscribe(REGISTER_COMMAND_TOPIC)
        print(f"📡 Subscribed to: {REGISTER_COMMAND_TOPIC}")
    else:
        print(f"❌ Failed to connect, code {rc}")

# ====================== Callback Saat Menerima Pesan ======================
def on_message(client, userdata, msg):
    global DEVICE_ID

    if msg.topic == REGISTER_COMMAND_TOPIC:
        try:
            payload = json.loads(msg.payload.decode())
            print(f"📨 Received registration command: {payload}")

            expected_keys = ["device_id", "device_token", "warning_level", "danger_level", "sensor_height"]
            if all(k in payload for k in expected_keys):
                DEVICE_ID = payload["device_id"]

                response = {
                    "device_id": DEVICE_ID,
                    "status": "registered",
                    "message": "Device successfully registered",
                    "timestamp": int(time.time())
                }

                client.publish(REGISTER_RESPONSE_TOPIC, json.dumps(response))
                print(f"📤 Sent registration response: {response}")

                # ✅ Mulai publish data setelah registrasi
                threading.Thread(target=publish_dummy_water_level, args=(client,), daemon=True).start()

            else:
                print("⚠️ Invalid registration command: missing required fields")

        except json.JSONDecodeError:
            print("❌ Invalid JSON received")

# ====================== Simulasi Publish Data ======================
def publish_dummy_water_level(client, interval=10):  # Ganti interval jika perlu
    while True:
        if DEVICE_ID != "":
            dummy_data = {
            "device_id": DEVICE_ID,
            "height": round(random.uniform(0.0, 100.0),2),  # Simulasi level air antara 0.0 hingga 1.0
            "timestamp": datetime.now().isoformat()
            }
            client.publish(WATERLEVEL_TOPIC, json.dumps(dummy_data))
            print(f"💧 Published water level: {dummy_data}")
        else:
            print("⏳ Waiting for DEVICE_ID...")
        time.sleep(interval)

# ====================== Fungsi Utama ======================
def run_simulated_device():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT)
        print(f"🚀 Simulated device running")
        client.loop_forever()
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        print("🛑 Stopping simulated device...")
        client.loop_stop()
        client.disconnect()

# ====================== Entry Point ======================
if __name__ == "__main__":
    run_simulated_device()
