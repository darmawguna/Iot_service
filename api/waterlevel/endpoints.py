from flask import Blueprint, jsonify, request
from influxdb_client import InfluxDBClient
from config.settings import Config
from helper.form_validation import get_form_data
from helper.json_formatter import create_response

# Inisialisasi InfluxDB Client
client = InfluxDBClient(url=Config.INFLUXDB_URL, token=Config.INFLUXDB_TOKEN, org=Config.INFLUXDB_ORG)
query_api = client.query_api()

# Blueprint untuk Water Level
waterlevel = Blueprint("waterlevel", __name__)

@waterlevel.route("/trend", methods=["POST"])
def get_water_level_trend():
    """
    Endpoint untuk mendapatkan tren analitik water level berdasarkan sensor_id dan rentang waktu.
    Contoh request:
    {
        "sensor_id": "sensor_1",
        "start": "-7d",
        "stop": "now"
    }
    """


    required = get_form_data(["sensor_id", "start", "stop"]) 
    sensor_id = required["sensor_id"]
    start = required["start"]  # Default 7 hari terakhir
    stop =required['stop'] # Default sekarang
    
    print(f"sensor_id: {sensor_id}, start: {start}, stop: {stop}")

    if not sensor_id:
        return jsonify({"error": "sensor_id is required"}), 400

    query = f"""
    from(bucket: "{Config.INFLUXDB_BUCKET}")
    |> range(start: time(v: "{start}"), stop: time(v: "{stop}"))
    |> filter(fn: (r) => r["_measurement"] == "WaterLevel")
    |> filter(fn: (r) => r["sensor_id"] == "{sensor_id}")
    |> filter(fn: (r) => r["_field"] == "water_level")
    |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
    |> yield(name: "mean")
    """
    
    result = query_api.query(org=Config.INFLUXDB_ORG, query=query)

    data_points = []
    for table in result:
        for record in table.records:
            data_points.append({
                "time": record.get_time().isoformat(),
                "water_level": record.get_value()
            })

    if not data_points:
        return jsonify({"message": "No data available for this sensor."})

    # Hitung analitik dasar
    water_levels = [d["water_level"] for d in data_points]

    trend_analysis = {
        "sensor_id": sensor_id,
        "start_time": data_points[0]["time"],
        "end_time": data_points[-1]["time"],
        "average_level": round(sum(water_levels) / len(water_levels), 2),
        "max_level": max(water_levels),
        "min_level": min(water_levels),
        "trend": "increasing" if water_levels[-1] > water_levels[0] else "decreasing"
    }
    
    response_data = {
        "analysis": trend_analysis,
        "records": data_points  # Menyertakan semua record hasil query
    }



    return create_response(
        data = response_data, 
        message = "Success get trend water level"
        )
    
    # return create_response(data=data, message="Debug get data form request")
    
@waterlevel.route("/latest", methods=["POST"])
def get_water_level_latest():
    # ...
    required = get_form_data(["sensor_id"])
    sensor_id = required["sensor_id"]

    if not sensor_id:
        return jsonify({"error": "sensor_id is required"}), 400

    # PERBAIKAN: Query disesuaikan dengan skema yang benar
    query = f"""
    from(bucket: "{Config.INFLUXDB_BUCKET}")
      |> range(start: -7d)
      |> filter(fn: (r) => r["_measurement"] == "water_level") 
      |> filter(fn: (r) => r["device_id"] == "{sensor_id}")
      |> filter(fn: (r) => r["_field"] == "height")
      |> last()
    """

    result = query_api.query(org=Config.INFLUXDB_ORG, query=query)

    latest_record = None
    for table in result:
        for record in table.records:
            latest_record = {
                "time": record.get_time().isoformat(),
                "height": record.get_value(), 
                "device_id": sensor_id
            }

    if not latest_record:
        return jsonify({"message": "No recent data found for this sensor."}), 404

    return create_response(data=latest_record, message="Success get latest water level")

@waterlevel.route("/test", methods=["GET"])
def test():
    return jsonify({
        "message": "Water Level API is working",
        "status": "success"
    }), 200