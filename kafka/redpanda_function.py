from confluent_kafka import Producer
import msgpack
import os
import logging
import threading

producer_config = {
    'bootstrap.servers': os.getenv('REDPANDA_BROKER', 'localhost:9092')
}
# producer = Producer(producer_config)

logger = logging.getLogger("MQTT_CLient")
logger.setLevel(logging.INFO)

# Cegah duplikasi handler
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def send_alert_data(sensor_id, water_level, threshold):
    """
    Mengirimkan data summary ke Redpanda dengan MessagePack dalam thread terpisah.
    """
    def publish():
        topic = os.getenv('ALERTING_TOPIC', 'alerts')
        alert_data = {
            "sensor_id": sensor_id,
            "water_level": water_level,
            "threshold": threshold,
            "status": "HIGH_WATER_LEVEL"
        }
        try:
            packed_data = msgpack.packb(alert_data)
            producer.produce(topic, packed_data)
            producer.flush()
            logger.info(f"🚨 Alert triggered: {alert_data}")
        except Exception as e:
            logger.error(f"Error sending data to Redpanda: {str(e)}")
    
    # Menjalankan fungsi publish di thread terpisah
    # thread = threading.Thread(target=publish, daemon=True)
    # thread.start()
