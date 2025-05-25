import json
import logging
import paho.mqtt.client as mqtt
import threading
import time
from config.settings import Config
# from influxdb.connection import write_data
from helper.statusIot_handler import handle_sensor_status
from helper.waterlevel_handler import handle_water_level
from queue import Queue

# MQTT client global variables
mqtt_client = None
stop_event = threading.Event()


# Tambahkan komponen baru untuk menunggu respon registrasi
response_queue = Queue()  # List untuk menyimpan beberapa response jika perlu
register_event = threading.Event()

def on_connect(client, userdata, flags, rc):
    """
    Callback function for when the client receives a CONNACK response from the server.

    The callback is called after the client calls connect(). The parameter rc is a boolean value with the following meaning:

    0: Connection successful
    1: Connection refused - incorrect protocol version
    2: Connection refused - invalid client identifier
    3: Connection refused - server unavailable
    4: Connection refused - bad username or password
    5: Connection refused - not authorized

    If the connection is successful, this function subscribes to the MQTT topics specified in the configuration file.
    """
    user = 0
    if rc == 0:
        print(f"✅ MQTT Connected Successfully! Client ID: {user}")
        client.subscribe([
            (Config.MQTT_TOPIC_WATERLEVEL, 0),
            (Config.MQTT_TOPIC_STATUS, 1),
            (Config.REGISTRATION_RESPONSE_TOPIC, 0)
        ])
    else:
        print(f"⚠ MQTT Connection failed with code {rc}")

def on_message(client, userdata, msg):
    """
    Callback function that processes incoming MQTT messages.

    The function decodes the message payload and routes it to the appropriate
    handler based on the topic. It also handles registration response messages
    by storing the response in a queue and setting an event flag.

    :param client: The MQTT client instance.
    :param userdata: The private user data as set in Client() or userdata_set().
    :param msg: An instance of MQTTMessage, which contains topic, payload, qos, retain.
    """
    try:
        payload = json.loads(msg.payload.decode())

        # Jika pesan dari topic registrasi
        if msg.topic == Config.REGISTRATION_RESPONSE_TOPIC:
            print(f"📥 Registration response received: {payload}")
            response_queue.put(payload)  # Simpan response ke dalam queue
            register_event.set()
            return

        # Jika bukan response registrasi, lanjut ke handler biasa
        # if sensor_id not in ALLOWED_SENSORS:
        #     print(f"❌ Unauthorized sensor: {sensor_id}")
        #     return

        if msg.topic == Config.MQTT_TOPIC_WATERLEVEL:
            handle_water_level(payload)
        elif msg.topic == Config.MQTT_TOPIC_STATUS:
            handle_sensor_status(payload)
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON received!")
    except KeyError as e:
        print(f"❌ Missing key in payload: {e}")
    except Exception as e:
        print(f"❌ Error processing message: {e}")


def on_disconnect(client, userdata, rc):
    """
    Callback function that is called when the client is disconnected from the MQTT broker.

    The function will continuously try to reconnect to the broker until the stop event is set.

    :param client: The MQTT client instance.
    :param userdata: The private user data as set in Client() or userdata_set().
    :param rc: The return code from the broker.
    """
    print(f"⚠ MQTT Disconnected! Trying to reconnect...")
    while not stop_event.is_set():
        try:
            client.reconnect()
            print(f"✅ Reconnected to MQTT!")
            return
        except Exception as e:
            print(f"❌ Reconnect failed: {e}")
            time.sleep(5)

def publish_command(device_id: str, payload: dict):

    """
    Publishes a command to a specific device via MQTT.

    :param device_id: The ID of the target device.
    :param payload: The command payload to send, as a dictionary.

    Raises:
        Exception: If the MQTT client is not initialized or not connected.
        Exception: If publishing the command fails.

    This function constructs a topic using the base command topic and the device ID,
    then publishes the provided payload as a JSON message to the MQTT broker.
    It checks for successful publication and logs the outcome.
    """

    if mqtt_client is None:
        raise Exception("MQTT client is not initialized. Please call start_mqtt() first.")

    if not mqtt_client.is_connected():
        raise Exception("MQTT client is not connected to broker.")

    try:
        topic = f"{Config.MQTT_BASE_TOPIC_COMMAND}/{device_id}/command"
        message = json.dumps(payload)

        result = mqtt_client.publish(topic, message)

        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise Exception(f"MQTT publish failed with code {result.rc}")
        else:
            print(f"📡 Command published to topic {topic}: {message}")

    except Exception as e:
        print(f"❌ Failed to publish command: {e}")

def wait_for_registration_response(device_id, timeout=15):
    """
    Waits for a registration response from a device with the given ID.

    :param device_id: The ID of the target device.
    :param timeout: The timeout in seconds to wait for the response, defaults to 15.

    :return: The registration response (dict) if received within the timeout, None otherwise.

    The function waits for the registration response event to be set, then checks
    if the response queue contains a message with the expected device ID. If yes,
    it returns the message. If the timeout is reached without receiving a response,
    it returns None.
    """
    print(f"⏳ Waiting for registration response from {device_id}...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        if register_event.wait(timeout=1):  # Tunggu event terlebih dahulu
            if not response_queue.empty():
                response = response_queue.get_nowait()
                if response.get("device_id") == device_id:
                    print(f"✅ Response received from {device_id}")
                    register_event.clear()
                    return response
            register_event.clear()

    print(f"⏰ Timeout: No response from {device_id}")
    return None

def publish_register_device(device_id: str, payload: dict):
    """
    Publishes a registration command to the MQTT broker and waits for a response
    from the target device.

    :param device_id: The ID of the target device.
    :param payload: The registration payload to send, as a dictionary.

    :return: The registration response (dict) if received within the timeout, None otherwise.

    The function first checks that the MQTT client is initialized and connected.
    It then constructs a topic using the base command topic and the device ID,
    and publishes the provided payload as a JSON message to the MQTT broker.
    It waits for a registration response message from the device and returns it
    if received within the timeout period. If the timeout is reached without
    receiving a response, it returns None. If any error occurs, it raises an exception.
    """
    if mqtt_client is None:
        raise Exception("MQTT client is not initialized. Please call start_mqtt() first.")

    if not mqtt_client.is_connected():
        raise Exception("MQTT client is not connected to broker.")

    try:
        topic = Config.REGISTRATION_REQUEST_TOPIC
        message = json.dumps(payload)
        print(f"📡 Publishing registration command to topic {topic}: {message}")

        result = mqtt_client.publish(topic, message)
        

        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise Exception(f"MQTT publish failed with code {result.rc}")
        else:
            print(f"📡 Command published to topic {topic}: {message}")

        # Tunggu respon dari device
        response = wait_for_registration_response(device_id, timeout=15)

        if response:
            print("✅ Device responded successfully:", response)
            return response
        else:
            print("❌ No response from device within timeout period.")
            return None

    except Exception as e:
        print(f"❌ Failed to publish or receive response: {e}")
        return None

# def subscribe_register_device():
#     if mqtt_client is None:
#         raise Exception("MQTT client is not initialized. Please call start_mqtt() first.")

#     if not mqtt_client.is_connected():
#         raise Exception("MQTT client is not connected to broker.")

#     try:
#         topic = f"{Config.MQTT_BASE_TOPIC_COMMAND}/register-device/response"
#         mqtt_client.subscribe(topic)
#         print(f"📡 Subscribed to topic: {topic}")
#     except Exception as e:
#         print(f"❌ Failed to subscribe: {e}")



def start_mqtt(max_retries=5, retry_delay=5):
    global mqtt_client
    if mqtt_client is not None:
        print(f"⚠ MQTT Client is already running!")
        return

    print(f"🚀 Starting MQTT Client...")
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.on_disconnect = on_disconnect

    for attempt in range(max_retries):
        try:
            print(f"📡 Attempting to connect to MQTT Broker (Attempt {attempt + 1}/{max_retries})...")
            mqtt_client.connect(Config.MQTT_BROKER, Config.MQTT_PORT, 60)
            mqtt_client.loop_start()
            print("✅ Successfully connected to MQTT Broker.")
            stop_event.wait()
            break  # Jika berhasil dan stop_event dipicu, keluar
        except Exception as e:
            print(f"❌ Connection attempt failed: {e}")
            if attempt < max_retries - 1:
                print(f"⏳ Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("❌ Max retries reached. Could not connect to MQTT Broker.")
        finally:
            stop_mqtt()

def stop_mqtt():
    global mqtt_client
    if stop_event.is_set():
        return
    stop_event.set()
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    # global mqtt_client
    mqtt_client = None  # Reset
    print(f"🛑 Stopped MQTT Client.")