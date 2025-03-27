from flask import Blueprint, jsonify
from influxdb.connection import influxdb
from config.settings import Config

api = Blueprint("api", __name__)



@api.route("/", methods=["GET"])
def test():
    return jsonify("test")

@api.route("/api/data/waterlevel", methods=["GET"])
def get_waterlevel():
    query = f'from(bucket: "{Config.INFLUXDB_BUCKET}") |> range(start: -1h) |> filter(fn: (r) => r._measurement == "waterlevel")'
    tables = influxdb.query_data(query)

    result = []
    for table in tables:
        for record in table.records:
            result.append({
                "sensor_id": record.values["sensor_id"],
                "water_level": record.get_value(),
                "timestamp": record.get_time()
            })

    return jsonify(result)

@api.route("/api/data/sensor_status", methods=["GET"])
def get_sensor_status():
    query = f'from(bucket: "{Config.INFLUXDB_BUCKET}") |> range(start: -1h) |> filter(fn: (r) => r._measurement == "sensor_status")'
    tables = influxdb.query_data(query)

    result = []
    for table in tables:
        for record in table.records:
            result.append({
                "sensor_id": record.values["sensor_id"],
                "battery": record.get_value() if record.field == "battery" else None,
                "latitude": record.get_value() if record.field == "latitude" else None,
                "longitude": record.get_value() if record.field == "longitude" else None,
                "timestamp": record.get_time()
            })

    return jsonify(result)
