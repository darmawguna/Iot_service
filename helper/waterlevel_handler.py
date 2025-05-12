from influxdb.connection import write_data
from influxdb_client import Point
from datetime import datetime
def handle_water_level(payload):
    water_level = float(payload.get("water_level", 0))
    # timestamp = payload.get("timestamp", "")
    timestamp_str = payload.get("timestamp")
    device_id = payload.get("device_id", "")
    timestamp = datetime.fromisoformat(timestamp_str)
    # TODO debugging penyimpanan data dari InfluxDB
    try:
        point = Point("DummyWaterLevel") \
            .tag("sensor_id", device_id) \
            .field("water_level", water_level) \
            .time(timestamp)
        
        write_data(point)
        # print(f"✅ Data successfully written to InfluxDB")
        # if water_level > threshold:
        #     # send_alert_data(payload["sensor_id"], water_level, threshold)
        #     print(f"⚠️ Water level {water_level} exceeds threshold {threshold}. Sending alert...")
        # else:
        #     print(f"✅ Water level {water_level} is normal.")
    except Exception as e:
        print(f"❌ Failed to write data to InfluxDB: {e}")
        
    

