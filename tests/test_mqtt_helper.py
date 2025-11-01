# File: tests/test_mqtt_helper.py

import pytest
from unittest.mock import MagicMock, patch

# Asumsikan class Anda ada di helper/mqtt_client.py
from mqtt.mqtt_client import MQTTHelper 

@pytest.fixture
def mqtt_helper():
    """
    Pytest Fixture: Membuat instance MQTTHelper baru untuk setiap tes.
    Ini memastikan setiap tes berjalan dalam kondisi yang bersih dan terisolasi.
    """
    return MQTTHelper()

def test_initialization(mqtt_helper):
    """Tes 1: Memastikan semua state diinisialisasi dengan benar."""
    assert mqtt_helper.client is None
    assert mqtt_helper.is_running is False
    assert len(mqtt_helper.whitelist_cache) == 0
    assert mqtt_helper.response_queue.empty()

def test_load_whitelist_success(mqtt_helper, mocker):
    """Tes 2: Memastikan whitelist berhasil dimuat dari backend."""
    # Siapkan mock untuk requests.get
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"device_ids": ["device-01", "device-02"]}
    mocker.patch('requests.get', return_value=mock_response)

    # Panggil method yang akan diuji
    mqtt_helper.load_whitelist_from_backend()

    # Assertasi
    assert "device-01" in mqtt_helper.whitelist_cache
    assert "device-02" in mqtt_helper.whitelist_cache
    assert len(mqtt_helper.whitelist_cache) == 2

def test_load_whitelist_failure(mqtt_helper, mocker):
    """Tes 3: Memastikan penanganan error saat gagal memuat whitelist."""
    # Siapkan mock untuk simulasi kegagalan request HTTP
    mocker.patch('requests.get', side_effect=requests.exceptions.RequestException("Connection failed"))

    mqtt_helper.load_whitelist_from_backend()

    # Assertasi: pastikan whitelist tetap kosong
    assert len(mqtt_helper.whitelist_cache) == 0

@patch('paho.mqtt.client.Client') # Mock class Client dari paho
def test_start_method_connects_and_loops(mock_mqtt_client_class, mqtt_helper, mocker):
    """Tes 4: Memastikan method start() mencoba koneksi dan memulai loop."""
    # Mock load_whitelist agar tidak melakukan request HTTP sungguhan
    mocker.patch.object(mqtt_helper, 'load_whitelist_from_backend')
    
    # Dapatkan instance dari mock client saat dibuat
    mock_client_instance = mock_mqtt_client_class.return_value
    
    # Panggil method start
    mqtt_helper.start()

    # Assertasi
    mock_mqtt_client_class.assert_called_once() # Pastikan client dibuat
    mock_client_instance.connect.assert_called_once() # Pastikan connect dipanggil
    mock_client_instance.loop_start.assert_called_once() # Pastikan loop dimulai
    assert mqtt_helper.is_running is True

def test_stop_method_disconnects(mqtt_helper):
    """Tes 5: Memastikan method stop() menghentikan loop dan diskonek."""
    # Siapkan kondisi seolah-olah client sedang berjalan
    mqtt_helper.is_running = True
    mqtt_helper.client = MagicMock()

    # Panggil method stop
    mqtt_helper.stop()

    # Assertasi
    mqtt_helper.client.loop_stop.assert_called_once()
    mqtt_helper.client.disconnect.assert_called_once()
    assert mqtt_helper.is_running is False
    
@patch('helper.mqtt_client.write_data') # Mock fungsi write_data
def test_on_message_handles_waterlevel_data_for_whitelisted_device(mock_write_data, mqtt_helper):
    """Tes 6: Memastikan on_message memproses data waterlevel dari device yang diizinkan."""
    # Setup
    mqtt_helper.whitelist_cache.add("device-01")
    
    mock_msg = MagicMock()
    mock_msg.topic = "iot/waterlevel" # Asumsi dari Config
    mock_msg.payload.decode.return_value = '{"device_id": "device-01", "height": 55.5}'
    
    # Panggil on_message
    mqtt_helper.on_message(None, None, mock_msg)
    
    # Assertasi
    mock_write_data.assert_called_once_with({"device_id": "device-01", "height": 55.5})

@patch('helper.mqtt_client.write_data')
def test_on_message_rejects_non_whitelisted_device(mock_write_data, mqtt_helper):
    """Tes 7: Memastikan on_message menolak data dari device yang tidak diizinkan."""
    # Setup (whitelist kosong)
    
    mock_msg = MagicMock()
    mock_msg.topic = "iot/waterlevel"
    mock_msg.payload.decode.return_value = '{"device_id": "device-hacker", "height": 999}'
    
    # Panggil on_message
    mqtt_helper.on_message(None, None, mock_msg)
    
    # Assertasi: write_data tidak boleh dipanggil
    mock_write_data.assert_not_called()

def test_on_message_handles_registration_response(mqtt_helper):
    """Tes 8: Memastikan on_message menangani respons registrasi dengan benar."""
    # Setup
    mock_msg = MagicMock()
    mock_msg.topic = "iot/register/response" # Asumsi dari Config
    response_payload = {"device_id": "device-new", "status": "success"}
    mock_msg.payload.decode.return_value = json.dumps(response_payload)
    
    # Pastikan event belum di-set sebelumnya
    assert not mqtt_helper.register_event.is_set()
    
    # Panggil on_message
    mqtt_helper.on_message(None, None, mock_msg)
    
    # Assertasi
    assert not mqtt_helper.response_queue.empty()
    assert mqtt_helper.response_queue.get() == response_payload
    assert mqtt_helper.register_event.is_set() # Pastikan event di-set

def test_publish_register_device_timeout(mqtt_helper, mocker):
    """Tes 9: Memastikan fungsi registrasi mengembalikan None jika timeout."""
    # Mock client agar terlihat running
    mqtt_helper.is_running = True
    mqtt_helper.client = MagicMock()
    
    # Mock register_event.wait() agar langsung mengembalikan False (timeout)
    mocker.patch.object(mqtt_helper.register_event, 'wait', return_value=False)
    
    response = mqtt_helper.publish_register_device("device-timeout", {"payload": "data"})
    
    # Assertasi
    assert response is None