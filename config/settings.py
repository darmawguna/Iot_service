import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # MQTT Configuration
    MQTT_BROKER = os.getenv("MQTT_BROKER")
    MQTT_PORT = int(os.getenv("MQTT_PORT"))
    MQTT_TOPIC_WATERLEVEL = os.getenv("MQTT_TOPIC_WATERLEVEL")
    MQTT_TOPIC_STATUS = os.getenv("MQTT_TOPIC_STATUS")
    REGISTRATION_RESPONSE_TOPIC = os.getenv("REGISTRATION_RESPONSE_TOPIC")
    REGISTRATION_REQUEST_TOPIC = os.getenv("REGISTRATION_REQUEST_TOPIC")
    MQTT_BASE_TOPIC_COMMAND = os.getenv("MQTT_BASE_TOPIC_COMMAND", "iot/sensor")

    # InfluxDB Configuration
    INFLUXDB_URL = os.getenv("INFLUXDB_URL")
    INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
    INFLUXDB_ORG = os.getenv("INFLUXDB_ORG")
    INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET")
