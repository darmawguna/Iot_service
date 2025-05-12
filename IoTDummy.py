import json
import random
import time
import paho.mqtt.client as mqtt
from datetime import datetime, timezone

# Konfigurasi MQTT Broker
MQTT_BROKER = "localhost"  # Ganti dengan alamat broker MQTT
MQTT_PORT = 1883
MQTT_TOPIC_WATERLEVEL = "iot/waterlevel"
MQTT_TOPIC_STATUS = "iot/status"

# Fungsi untuk membuat data dummy ketinggian air
def generate_dummy_waterlevel():
    sensor_id = 0
    return {
        "sensor_id": 1,
        "water_level": round(random.uniform(20, 40)),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# Fungsi untuk membuat data dummy status sensor
def generate_dummy_status():
    return {
        "sensor_id": f"sensor_{random.randint(1, 10)}",
        "battery": random.randint(10, 100),
        "location": {
            "latitude": round(random.uniform(-7.0, -6.5), 6),
            "longitude": round(random.uniform(107.5, 108.0), 6)
        },
        "timestamp": int(time.time())
    }

# Fungsi untuk mengirim data dummy ke broker MQTT
def publish_dummy_data(client):
    while True:
        # # Generate dan kirim data water level
        waterlevel_payload = generate_dummy_waterlevel()
        client.publish(MQTT_TOPIC_WATERLEVEL, json.dumps(waterlevel_payload))
        print(f"Sent Water Level Data: {waterlevel_payload}")
        
        # Generate dan kirim data status sensor
        # status_payload = generate_dummy_status()
        # client.publish(MQTT_TOPIC_STATUS, json.dumps(status_payload))
        # print(f"Sent Sensor Status Data: {status_payload}")
        
        time.sleep(15)  # Mengirim data setiap 15 detik

# Fungsi utama untuk memulai client MQTT
def main():
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    publish_dummy_data(client)

if __name__ == "__main__":
    main()
