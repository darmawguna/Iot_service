from flask import Blueprint, jsonify, request
from config.settings import Config
from helper.form_validation import get_form_data
from helper.json_formatter import create_response
from mqtt.client import publish_command, publish_register_device  # pastikan kamu import fungsi ini

import json

# Blueprint untuk Water Level
iotdevice = Blueprint("iotdevice", __name__)

@iotdevice.route("/threshold", methods=["POST"])
def set_threshold_iotdevice():
    required = get_form_data(["sensor_id", "warning_level", "danger_level", "sensor_height"]) 
    sensor_id = required["sensor_id"]
    warning_level = required["warning_level"]
    danger_level = required["danger_level"]
    sensor_height = required["sensor_height"]

    payload = {
        "warning_level": warning_level,
        "danger_level": danger_level,
        "sensor_height": sensor_height,
        "sensor_id": sensor_id
    }
    
    print(f"📨 Received threshold command: {payload}")

    try:
        publish_command(sensor_id, payload)
        return create_response(
            data=payload,
            message="Threshold command published to MQTT successfully"
        )
    except Exception as e:
        return create_response(success=False, message=str(e)), 500
    

@iotdevice.route("/register-device", methods=["POST"])
def register_device():
    required = get_form_data(["device_id", "device_token", "warning_level", "danger_level", "sensor_height"]) 
    device_id = required["device_id"]
    device_token = required["device_token"]
    warning_level = required["warning_level"]
    danger_level = required["danger_level"]
    sensor_height = required["sensor_height"]

    payload = {
        "device_id": device_id,
        "device_token": device_token,
        "warning_level": warning_level,
        "danger_level": danger_level,
        "sensor_height": sensor_height,
    }

    try:
        # Kirim command + tunggu respon
        response = publish_register_device(device_id, payload)

        if response and response.get("status") == "success":
            return create_response(
                data=response,
                message="Device registered successfully"
            )
        else:
           return create_response(data="",message="No response from device", status=408) 

    except Exception as e:
        return create_response(success=False, message=str(e)), 500