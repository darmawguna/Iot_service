import logging
import threading
import signal
import sys
import time

from server.server import run_server
from websocket.websocket import websocket_start, stop_websocket

from mqtt.mqtt_client import mqtt_helper 

def signal_handler(sig, frame):
    """Menangani shutdown aplikasi dengan rapi."""
    print("\n🛑 Caught shutdown signal. Stopping all services...")
    mqtt_helper.stop()
    # stop_websocket()
    time.sleep(1)
    sys.exit(0)


if __name__ == "__main__":
    print("🚀 Starting IoT Gateway Server...")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    mqtt_thread = threading.Thread(target=mqtt_helper.start, daemon=True)
    mqtt_thread.start()

    # Jalankan server Flask di thread utama (ini akan memblokir)
    run_server()