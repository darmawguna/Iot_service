from confluent_kafka import Consumer, KafkaException
import os
import msgpack

# Konfigurasi Consumer
conf = {
    'bootstrap.servers': os.getenv('REDPANDA_BROKER', 'localhost:9092'),
    'group.id': 'alert_processor',
    'auto.offset.reset': 'earliest',  # Bisa diubah ke 'latest' jika ingin membaca pesan baru saja
    'enable.auto.commit': True  # Agar offset otomatis diperbarui
}

consumer = Consumer(conf)
topic = os.getenv('ALERTING_TOPIC', 'alerts')
consumer.subscribe([topic])

def process_alert():
    """Menerima dan memproses alert dari Redpanda."""
    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print(f"❌ Kafka error: {msg.error()}")
                continue
            
            try:
                unpacked_data = msgpack.unpackb(msg.value(), raw=False)
                print(f"🚨 Received Alert: {unpacked_data}")
            except Exception as e:
                print(f"❌ Failed to unpack message: {e}")
    except KeyboardInterrupt:
        print("❌ Consumer stopped.")
    finally:
        consumer.close()  # Pastikan consumer ditutup dengan benar

if __name__ == "__main__":
    process_alert()
