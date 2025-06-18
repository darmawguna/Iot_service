import logging
import traceback
from influxdb_client import InfluxDBClient
from config.settings import Config


# Setup Logger
logger = logging.getLogger("MQTT_Client")
logger.setLevel(logging.INFO)

if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def connect_influxdb():
    """Create and return a write API for InfluxDB"""
    logger.info("🔌 Attempting to connect to InfluxDB...")
    try:
        client = InfluxDBClient(
            url=Config.INFLUXDB_URL,
            token=Config.INFLUXDB_TOKEN,
            org=Config.INFLUXDB_ORG
        )
        write_api = client.write_api()
        logger.info("✅ Successfully connected to InfluxDB")
        return write_api
    except Exception as e:
        logger.error("❌ Failed to connect to InfluxDB", exc_info=True)
        return None

# Singleton instance of write API
influxdb = connect_influxdb()

def write_data(point):
    """
    Write a single data point to InfluxDB.
    
    :param point: A data point object compatible with InfluxDB.
    """
    if not influxdb:
        logger.error("🚫 No InfluxDB connection. Cannot write data.")
        return

    try:
        influxdb.write(bucket=Config.INFLUXDB_BUCKET, record=point)
        logger.info(f"📊 Data written to InfluxDB: {point.to_line_protocol()}")
    except Exception as e:
        logger.error("❌ Error occurred while writing to InfluxDB", exc_info=True)
        logger.debug(f"Failed point data: {point}")
