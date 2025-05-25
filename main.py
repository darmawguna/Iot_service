import logging
import threading
import signal
import sys
from mqtt.client import start_mqtt, stop_mqtt
from server.server import run_server
from websocket.websocket import websocket_start, stop_websocket

def signal_handler(sig, frame):
    """Menangani shutdown aplikasi"""
    # logging.info("🛑 Caught shutdown signal. Stopping MQTT & Flask...")
    print(f"🛑 Caught shutdown signal. Stopping MQTT & Flask...")
    
    # Hentikan MQTT Client dengan baik
    stop_mqtt()
    stop_websocket()

    # Exit aplikasi
    sys.exit(0)


if __name__ == "__main__":
    # logging.info("🚀 Starting IoT Gateway Server...")
    print(f"🚀 Starting IoT Gateway Server...")

    # Tangani sinyal Ctrl+C atau termination
    signal.signal(signal.SIGINT, signal_handler)

    # # Jalankan MQTT client di thread terpisah
    mqtt_thread = threading.Thread(target=start_mqtt, daemon=True)
    mqtt_thread.start()
    websocket_thread = threading.Thread(target=websocket_start, daemon=True)
    websocket_thread.start()

    # Jalankan server Flask
    run_server()
