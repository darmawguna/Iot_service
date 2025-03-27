
import json
import logging
import paho.mqtt.client as mqtt
import threading
import time
from config.settings import Config
from influxdb.connection import write_data
from influxdb_client import Point
from kafka.redpanda_function import send_alert_data


# logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

logger = logging.getLogger("MQTT_CLient")
logger.setLevel(logging.INFO)

# ALLOWED SENSOR ID
ALLOWED_SENSORS = {
    "1": "Lokasi A",
    "sensor-2": "Lokasi B",
    "sensor-3": "Lokasi C"
}

# Cegah duplikasi handler
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Event untuk menghentikan MQTT saat Flask berhenti
stop_event = threading.Event()

def on_connect(client, userdata, flags, rc):
    user = 0
    if rc == 0:
        # logger.info("✅ MQTT Connected Successfully!")
        logger.info(f"✅ MQTT Connected Successfully! Client ID: {user + 1}")
        client.subscribe([(Config.MQTT_TOPIC_WATERLEVEL, 0), (Config.MQTT_TOPIC_STATUS, 0)])
    else:
        logger.warning(f"⚠ MQTT Connection failed with code {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        sensor_id = payload.get("sensor_id")
        water_level = float(payload.get("water_level", 0))
        timestamp = payload.get("timestamp")
        if sensor_id not in ALLOWED_SENSORS:
            print(f"❌ Unauthorized sensor: {sensor_id}")
            return
        
        # code untuk anomali data waterlevel
        # if water_level < 0 or water_level > 500:  # Misalnya, batas wajar 0-500 cm
        #     print(f"⚠️ Invalid water level: {water_level} from {sensor_id}")
        #     return
        if msg.topic == Config.MQTT_TOPIC_WATERLEVEL:
            # code untuk mengirim data ke influxdb
            # point = Point("waterlevel") \
            #     .tag("sensor_id", payload["sensor_id"]) \
            #     .field("water_level", float(payload["water_level"])) \
            #     .time(payload["timestamp"])
            logger.info(f"📡 DEBUG:  Received Sensor Water Data: {msg.topic}: {payload}")
            threshold = 4.0  # Contoh threshold
            
            # code untuk alerting
            # if payload["water_level"] > threshold:
            #     send_alert_data(payload["sensor_id"],  payload["water_level"], threshold)
            #     # logger.info(f"⚠️ Water level {payload['water_level']} exceeds threshold {threshold}. Sending alert...")
            # else:
            #     logger.info(f"✅ Water level {payload['water_level']} is normal.")
            # logging.info(f"📡 Received Sensor Water Data: {msg.topic}: {payload}")
        elif msg.topic == Config.MQTT_TOPIC_STATUS:
            # code untuk mengirim data status ke influxdb
            # point = Point("sensor_status") \
            #     .tag("sensor_id", payload["sensor_id"]) \
            #     .field("battery", int(payload["battery"])) \
            #     .field("latitude", float(payload["location"]["latitude"])) \
            #     .field("longitude", float(payload["location"]["longitude"])) \
            #     .time(payload["timestamp"])
            logger.info(f"📡 Received Sensor Status Data: {msg.topic}: {payload}")

        # write_data(point)
    except json.JSONDecodeError:
        logger.error("❌ Invalid JSON received!")
    except KeyError as e:
        logger.error(f"❌ Missing key in payload: {e}")
    except Exception as e:
        logger.error(f"❌ Error processing message: {e}")

def on_disconnect(client, userdata, rc):
    logger.warning("⚠ MQTT Disconnected! Trying to reconnect...")
    while not stop_event.is_set():
        try:
            client.reconnect()
            logger.info("✅ Reconnected to MQTT!")
            return
        except Exception as e:
            logger.error(f"❌ Reconnect failed: {e}")
            time.sleep(5)



def start_mqtt():
    """Memulai MQTT Client"""
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    try:
        client.connect(Config.MQTT_BROKER, Config.MQTT_PORT, 60)
        client.loop_start()
        logger.info("🚀 MQTT Client started")

        # Menunggu event stop
        stop_event.wait()

    except Exception as e:
        logger.error(f"❌ Failed to start MQTT Client: {e}")
    finally:
        logger.info("🛑 Stopping MQTT Client...")
        client.loop_stop()
        client.disconnect()

def stop_mqtt():
    """Menghentikan MQTT Client"""
    stop_event.set()
    logger.info("🛑 Stopping MQTT Client...")