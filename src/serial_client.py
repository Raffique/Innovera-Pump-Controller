import serial_client
import json
import time
import threading

class SerialClient:
    def __init__(self):
        self.ser = None
        self.lock = threading.Lock()  # Mutex for thread-safe access
        self.running = True           # Control flag for the thread
        self.message_thread = None    # Thread for listening to messages

        # Try to establish connection
        self.reconnect()

        # Start the on_message thread
        self.message_thread = threading.Thread(target=self.on_messages)
        self.message_thread.daemon = True
        self.message_thread.start()

    def on_connect(self):
        pass

    def on_disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    def on_messages(self, callback):
        """Thread function to continuously listen for messages."""
        while self.running:
            with self.lock:  # Ensure exclusive access to the serial port
                if self.ser and self.ser.is_open:
                    try:
                        if self.ser.in_waiting > 0:
                            line = self.ser.readline().decode('utf-8').rstrip()
                            try:
                                data = json.loads(line)  # Parse JSON data
                                callback(data)  # Process the data
                            except json.JSONDecodeError as e:
                                print(f"Invalid JSON received: {line} - {e}")
                            self.ser.flush()
                    except serial_client.SerialException as e:
                        print(f"Serial connection error: {e}")
                        self.reconnect()
            time.sleep(0.1)  # Prevent CPU overuse

    def send(self, data):
        """Send data over the serial connection."""
        with self.lock:  # Ensure exclusive access to the serial port
            try:
                if self.ser and self.ser.is_open:
                    json_data = json.dumps(data) + '\n'
                    self.ser.write(json_data.encode('utf-8'))  # Encode as bytes and send
                    print(f"Sent data: {json_data}")
            except serial_client.SerialException as e:
                print(f"Error sending data: {e}")
                self.reconnect()

    def is_connected(self):
        """Check if the serial connection is active."""
        with self.lock:
            return self.ser and self.ser.is_open

    def reconnect(self):
        """Attempt to reconnect the serial connection."""
        print("Attempting to reconnect serial")
        while True:
            try:
                with self.lock:  # Lock the port during reconnect attempts
                    self.ser = serial_client.Serial('/dev/ttyACM0', 115200, timeout=1)
                    print("Reconnected on /dev/ttyACM0")
                    break
            except:
                try:
                    with self.lock:
                        self.ser = serial_client.Serial('/dev/ttyUSB0', 115200, timeout=1)
                        print("Reconnected on /dev/ttyUSB0")
                        break
                except:
                    print("Reconnection failed, retrying in 3 seconds...")
                    time.sleep(3)

    def stop(self):
        """Gracefully stop the client."""
        self.running = False
        if self.message_thread.is_alive():
            self.message_thread.join()
        self.on_disconnect()

if __name__ == "__main__":
    client = SerialClient()

    def test_callback(data):
        print(f"Callback received: {data}")

    try:
        while True:
            # Simulate sending data every 2 seconds
            data = {"message": "Hello from client"}
            client.send(data)
            time.sleep(2)
    except KeyboardInterrupt:
        print("Shutting down gracefully...")
        client.stop()
