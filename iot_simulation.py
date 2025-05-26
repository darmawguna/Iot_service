import paho.mqtt.client as mqtt
import json
import time
import random
import string
from datetime import datetime
import threading
WATERLEVEL_TOPIC = "iot/waterlevel"

# Konfigurasi MQTT
MQTT_BROKER = "localhost"  # Ganti sesuai alamat broker Anda
MQTT_PORT = 1883
REGISTER_COMMAND_TOPIC = "iot/register-device/request"
REGISTER_RESPONSE_TOPIC = "iot/register-device/response"

# Simulasi ID perangkat acak saat boot
def generate_random_device_id(prefix="SIM-"):
    return prefix + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

DEVICE_ID = "53e3eb94-7ea4-4c17-b7b8-a2795908b221"
print(f"📱 Simulated Device Booted with ID: {DEVICE_ID}")

# Callback ketika klien terhubung ke broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ MQTT Connected")
        client.subscribe(REGISTER_COMMAND_TOPIC)
        print(f"📡 Subscribed to: {REGISTER_COMMAND_TOPIC}")
    else:
        print(f"❌ Failed to connect, code {rc}")

# Callback untuk menerima pesan
def on_message(client, userdata, msg):
    if msg.topic == REGISTER_COMMAND_TOPIC:
        try:
            payload = json.loads(msg.payload.decode())
            print(f"📨 Received registration command: {payload}")

            # Validasi minimal payload
            expected_keys = ["device_id", "device_token", "warning_level", "danger_level", "sensor_height"]
            if all(k in payload for k in expected_keys):
                response = {
                    "device_id": payload["device_id"],
                    "status": "registered",
                    "message": "Device successfully registered",
                    "timestamp": int(time.time())
                }

                client.publish(REGISTER_RESPONSE_TOPIC, json.dumps(response))
                print(f"📤 Sent registration response: {response}")
            else:
                print("⚠️ Invalid registration command: missing required fields")

        except json.JSONDecodeError:
            print("❌ Invalid JSON received")
            
def publish_dummy_water_level(client, interval=5):
    while True:
        dummy_data = {
            "device_id": DEVICE_ID,
            "water_level": round(random.uniform(0.0, 5.0), 2),
            # "timestamp": int(time.time())
            # "timestamp": datetime.utcnow().isoformat()
            "timestamp": datetime.now().isoformat()
        }
        client.publish(WATERLEVEL_TOPIC, json.dumps(dummy_data))
        print(f"💧 Published water level: {dummy_data}")
        time.sleep(interval)

# Fungsi utama
def run_simulated_device():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT)
        print(f"🚀 Simulated device running with ID: {DEVICE_ID}")
        # Mulai thread publish dummy water level
        threading.Thread(target=publish_dummy_water_level, args=(client,), daemon=True).start()
        client.loop_forever()
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        print("🛑 Stopping simulated device...")
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    run_simulated_device()