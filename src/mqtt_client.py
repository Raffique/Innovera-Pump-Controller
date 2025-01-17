import paho.mqtt.client as mqtt
import json
import time
import threading

class MQTTClient:
    def __init__(self, id, broker="localhost", port=1883, topic="test/topic", alive_pulse_interval=2, callback=None):
        self.id = id
        self.broker = broker
        self.port = port
        self.topic = topic
        self.alive_pulse_interval = alive_pulse_interval
        self.callback = callback

        self.mqtt_connected = False
        self.reconnect_thread_active = False
        self.lock = threading.Lock()
        self.last_message_time = time.time()
        self.initial_connection = False


        
        self.mqtt_client = mqtt.Client(
            client_id=self.id,
            protocol=mqtt.MQTTv311,
            userdata=None, 
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2
        )
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_disconnect = self.on_disconnect

        # self.mqtt_client.connect(self.broker, self.port)
        # self.mqtt_client.subscribe(self.topic)
        # self.mqtt_client.loop_start()

        try:
            self.mqtt_client.connect(self.broker, self.port)
            self.mqtt_client.subscribe(self.topic)
            self.mqtt_client.loop_start()
            self.initial_connection = True
        except Exception as e:
            self.start_reconnect_thread()

    def on_connect(self, client, userdata, flags, rc, properties=None):
        print(f"Connected to MQTT broker with result code {rc}")
        # Resubscribe to topics on reconnect
        if rc == 0:
            with self.lock:
                self.mqtt_connected = True
                self.reconnect_thread_active = False
            self.mqtt_client.subscribe(self.topic)
        else:
            print(f"Failed to connect with result code: {rc}")
            self.mqtt_connected = False


    def on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        print(f"Disconnected from MQTT broker with reason code: {reason_code}")
        with self.lock:
            self.mqtt_connected = False
        if reason_code != 0:
            self.start_reconnect_thread()

    def on_message(self, client, userdata, message):
        try:
            #print("on message mqtt")
            data = json.loads(message.payload.decode())
            self.callback(data)
            self.last_message_time = time.time()
        except json.JSONDecodeError:
            print(f"Invalid MQTT message: {message.payload.decode()}")

    def send(self, data):
        try:
            json_data = json.dumps(data)
            self.mqtt_client.publish(self.topic, json_data)
        except Exception as e:
            print(f"Failed to send data: {e}")

    def reconnect(self):
        try:
            #print("Attempting to reconnect...")
            if self.initial_connection:
                self.mqtt_client.reconnect()
            else:
                self.mqtt_client.connect(self.broker, self.port)
                self.mqtt_client.subscribe(self.topic)
                self.mqtt_client.loop_start()
                self.initial_connection = True
        except Exception as e:
            time.sleep(5)
            self.reconnect()

    def start_reconnect_thread(self):
        self.reconnect_thread_active = True
        threading.Thread(target=self.reconnect, daemon=True).start()

    def alive_pulse(self):
        data = {"station_id": self.id, "status": "ALIVE"}
        self.send(data)

    def check_connection(self):
        # Check if no message has been received in a given timeout period
        if not self.mqtt_connected:
            self.start_reconnect_thread()

    def is_connected(self):
        return self.mqtt_client.is_connected()

    def cleanup(self):
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()


def test_callback(data):
    print(f"Received callback data: {data}")


if __name__ == "__main__":
    client = MQTTClient(id="client_1", broker='192.168.100.69', callback=test_callback, alive_pulse_interval=5)

    try:
        # Simulate sending alive pulses periodically
        while True:

            # Send test data every 3 seconds
            data = {"message": f"Heartbeat from {client.id}"}
            client.send(data)

            time.sleep(3)

    except KeyboardInterrupt:
        print("Shutting down MQTT client...")
        client.cleanup()

    except Exception as e:
        print(f"Final Error {e}")
