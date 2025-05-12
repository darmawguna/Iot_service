import json
import logging
import paho.mqtt.client as mqtt
import threading
import time
from config.settings import Config
# from influxdb.connection import write_data
from helper.statusIot_handler import handle_sensor_status
from helper.waterlevel_handler import handle_water_level


# MQTT client global variables
mqtt_client = None
stop_event = threading.Event()

# Allowed Sensor IDs
ALLOWED_SENSORS = {"1": "Lokasi A", "sensor-2": "Lokasi B", "sensor-3": "Lokasi C"}

def on_connect(client, userdata, flags, rc):
    user = 0
    if rc == 0:
        print(f"✅ MQTT Connected Successfully! Client ID: {user}")
        client.subscribe([(Config.MQTT_TOPIC_WATERLEVEL, 0), (Config.MQTT_TOPIC_STATUS, 0)])
    else:
        print(f"⚠ MQTT Connection failed with code {rc}")

def on_message(client, userdata, msg):
    
    try:
        payload = json.loads(msg.payload.decode())
        sensor_id = payload.get("sensor_id")
        timestamp = payload.get("timestamp")
        
        # if sensor_id not in ALLOWED_SENSORS:
        #     print(f"❌ Unauthorized sensor: {sensor_id}")
        #     return
        
        if msg.topic == Config.MQTT_TOPIC_WATERLEVEL:
            handle_water_level(payload)
        elif msg.topic == Config.MQTT_TOPIC_STATUS:
            handle_sensor_status(payload)
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON received!")
    except KeyError as e:
        print(f"❌ Missing key in payload: {e}")
    except Exception as e:
        print(f"❌ Error processing message: {e}")


def on_disconnect(client, userdata, rc):
    print(f"⚠ MQTT Disconnected! Trying to reconnect...")
    while not stop_event.is_set():
        try:
            client.reconnect()
            print(f"✅ Reconnected to MQTT!")
            return
        except Exception as e:
            print(f"❌ Reconnect failed: {e}")
            time.sleep(5)

def publish_command(device_id: str, payload: dict):
    """
    Publish perintah ke MQTT topic menggunakan client global yang sudah terkoneksi.
    """

    if mqtt_client is None:
        raise Exception("MQTT client is not initialized. Please call start_mqtt() first.")

    if not mqtt_client.is_connected():
        raise Exception("MQTT client is not connected to broker.")

    try:
        topic = f"{Config.MQTT_BASE_TOPIC_COMMAND}/{device_id}/command"
        message = json.dumps(payload)

        result = mqtt_client.publish(topic, message)

        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise Exception(f"MQTT publish failed with code {result.rc}")
        else:
            print(f"📡 Command published to topic {topic}: {message}")

    except Exception as e:
        print(f"❌ Failed to publish command: {e}")

def publish_register_device(device_id: str, payload: dict):
    """
    Publish perintah ke MQTT topic menggunakan client global yang sudah terkoneksi.
    """

    if mqtt_client is None:
        raise Exception("MQTT client is not initialized. Please call start_mqtt() first.")

    if not mqtt_client.is_connected():
        raise Exception("MQTT client is not connected to broker.")

    try:
        topic = f"{Config.MQTT_BASE_TOPIC_COMMAND}/register-device/command"
        message = json.dumps(payload)

        result = mqtt_client.publish(topic, message)

        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise Exception(f"MQTT publish failed with code {result.rc}")
        else:
            print(f"📡 Command published to topic {topic}: {message}")

    except Exception as e:
        print(f"❌ Failed to publish command: {e}")



def start_mqtt():
    global mqtt_client
    if mqtt_client is not None:
        print(f"⚠ MQTT Client is already running!")
        return
    
    print(f"🚀 Starting MQTT Client...")
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.on_disconnect = on_disconnect
    
    try:
        mqtt_client.connect(Config.MQTT_BROKER, Config.MQTT_PORT, 60)
        mqtt_client.loop_start()
        stop_event.wait()
    except Exception as e:
        print(f"❌ Failed to start MQTT Client: {e}")
    finally:
        stop_mqtt()

def stop_mqtt():
    if stop_event.is_set():
        return
    stop_event.set()
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    # logger.info("🛑 Stopped MQTT Client.")
    print(f"🛑 Stopped MQTT Client.")