from influxdb.connection import write_data
from influxdb_client import Point
from dateutil import parser
from datetime import datetime

def handle_water_level(payload):
    try:
        water_level = float(payload.get("water_level", 0))
        timestamp_str = payload.get("timestamp")
        device_id = payload.get("device_id", "")
        print(f"📡 Received water level data: {water_level} at {timestamp_str} for device {device_id}")

        if not timestamp_str or not device_id:
            print("⚠️ Incomplete payload, skipping Influx write.")
            return

        timestamp = parser.isoparse(timestamp_str)

        point = Point("WaterLevelSensor") \
            .tag("device_id", device_id) \
            .field("water_level", water_level) \
            .time(timestamp)
        write_data(point)
    except Exception as e:
        print(f"❌ Failed to write data to InfluxDB: {e}")
