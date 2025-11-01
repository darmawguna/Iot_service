from datetime import datetime
from influxdb.connection import connect_influxdb
from config.settings import Config
from influxdb_client import Point
import logging

logger = logging.getLogger("InfluxDBWriter")
logger.setLevel(logging.INFO)

if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

write_api = connect_influxdb()

def write_data(data):
    """
    Menulis satu data point ke InfluxDB dengan skema yang sudah disatukan.
    """
    try:
        if not write_api:
            logger.error("❌ Koneksi ke InfluxDB (write_api) gagal didapatkan.")
            return None

        # PERBAIKAN: Ambil 'height' dari data, bukan 'water_level'
        device_id = data.get("device_id")
        water_level = data.get("water_level") # <-- Menggunakan 'water_level' agar cocok dengan simulator

        if not device_id or water_level is None:
            logger.warning(f"⚠️ Data tidak lengkap, dilewati: {data}")
            return None

        # PERBAIKAN: Gunakan skema yang konsisten
        point = Point("TestingIoTFinal") \
            .tag("device_id", device_id) \
            .field("water_level", float(water_level))
        
        line_protocol = point.to_line_protocol()
        logger.info(f"📤 Menulis data: {line_protocol}")
        
        write_api.write(
            bucket=Config.INFLUXDB_BUCKET,
            org=Config.INFLUXDB_ORG, 
            record=point
        )

        logger.info("✅ Data berhasil ditulis ke InfluxDB.")
        return "Data written successfully"

    except ValueError:
        logger.error(f"❌ Tipe data height tidak valid: {data.get('height')}")
        return None
    except Exception as e:
        logger.error(f"❌ Terjadi exception saat menulis ke InfluxDB: {e}")
        logger.exception("Traceback:")
        return None
