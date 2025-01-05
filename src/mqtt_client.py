import paho.mqtt.client as mqtt
import json
import time

class MQTTClient:
    def __init__(self, id, broker="localhost", port=1883, topic="test/topic", alive_pulse_interval=2, callback=None):
        self.id = id
        self.broker = broker
        self.port = port
        self.topic = topic
        self.alive_pulse_interval = alive_pulse_interval
        self.callback = callback

        self.mqtt_connected = False
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
            self.reconnect()

    def on_connect(self, client, userdata, flags, rc, properties=None):
        print(f"Connected to MQTT broker with result code {rc}")
        # Resubscribe to topics on reconnect
        if rc == 0:
            self.mqtt_client.subscribe(self.topic)
            self.mqtt_connected = True
        else:
            print(f"Failed to connect with result code: {rc}")
            self.mqtt_connected = False


    def on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        print(f"Disconnected from MQTT broker with reason code: {reason_code}")
        self.mqtt_connected = False
        if reason_code != 0:
            self.reconnect()

    def on_message(self, client, userdata, message):
        try:
            data = json.loads(message.payload.decode())
            #if data.get("station_id") != self.id and self.callback:
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
            print("Attempting to reconnect...")
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

    def alive_pulse(self):
        data = {"station_id": self.id, "status": "ALIVE"}
        self.send(data)

    def check_connection(self):
        # Check if no message has been received in a given timeout period
        if not self.mqtt_connected:
            self.reconnect()

    def is_connected(self):
        return self.mqtt_client.is_connected()

    def cleanup(self):
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()


def test_callback(data):
    print(f"Received callback data: {data}")


if __name__ == "__main__":
    client = MQTTClient(id="client_1", broker='172.16.15.169', callback=test_callback, alive_pulse_interval=5)

    try:
        # Simulate sending alive pulses periodically
        while True:
            client.alive_pulse()

            # Send test data every 3 seconds
            data = {"message": f"Heartbeat from {client.id}"}
            client.send(data)

            time.sleep(3)

    except KeyboardInterrupt:
        print("Shutting down MQTT client...")
        client.cleanup()

    except Exception as e:
        print(f"Final Error {e}")
