import json
import paho.mqtt.client as mqtt
from flask import Flask
from flask_socketio import SocketIO
from config.settings import Config

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

def on_connect(client, userdata, flags, rc):
    print("✅ Connected to MQTT Broker")
    client.subscribe([
        (Config.MQTT_TOPIC_WATERLEVEL, 0),
    ])

def on_message(client, userdata, msg):
    try:
        parsed_message = json.loads(msg.payload.decode())
        if not parsed_message:
            print("⚠️ Received empty message from MQTT")
            return
        # print(f"📡 MQTT Data: {msg.topic} -", parsed_message)
        socketio.emit("water-level", parsed_message)  # Kirim ke semua client yang terhubung
    except json.JSONDecodeError as e:
        print("❌ Error processing MQTT message:", e)

@socketio.on('connect')
def handle_connect():
    print("✅ Client connected to WebSocket")
    # Anda bisa mengirim pesan ke klien jika diperlukan
    socketio.emit("message", {"data": "Welcome to the WebSocket server!"})
    
@socketio.on('disconnect')
def handle_disconnect():
    print("❌ Client disconnected from WebSocket")

@socketio.on('message')
def handle_message(message):
    print(f"📩 Received message from client: {message}")
    # Anda bisa memproses pesan dari klien jika diperlukan
    socketio.emit("message", {"data": "Message received!"})

def websocket_start():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(Config.MQTT_BROKER, Config.MQTT_PORT, 60)
    except Exception as e:
        print(f"❌ Failed to connect to MQTT Broker: {e}")
        return
    
    client.loop_start()
    socketio.run(app, host='0.0.0.0', port=3000)

def stop_websocket():
    # Hentikan MQTT client dan server Flask
    socketio.stop()
