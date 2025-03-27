import logging
from influxdb_client import InfluxDBClient
from config.settings import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def connect_influxdb():
    try:
        client = InfluxDBClient(url=Config.INFLUXDB_URL, token=Config.INFLUXDB_TOKEN, org=Config.INFLUXDB_ORG)
        write_api = client.write_api()
        logging.info("✅ Connected to InfluxDB")
        return write_api
    except Exception as e:
        logging.error(f"❌ Failed to connect to InfluxDB: {e}")
        return None

# Singleton instance
influxdb = connect_influxdb()

def write_data(point):
    """Fungsi untuk menyimpan data ke InfluxDB."""
    try:
        influxdb.write(bucket=Config.INFLUXDB_BUCKET, record=point)
        logging.info(f"📊 Data written to InfluxDB: {point.to_line_protocol()}")
    except Exception as e:
        logging.error(f"❌ Error writing to InfluxDB: {e}")
