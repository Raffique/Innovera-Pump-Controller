import mqtt_client
import serial_client
import json
import time
from typing import Optional, Dict
import threading

class PumpStation:
    def __init__(self, station_id: int, control_pump: bool = True, has_tank: bool = True, broker="localhost"):
        self.station_id = station_id
        self.control_pump = control_pump
        self.has_tank = has_tank
        
        # Station state tracking
        self.pressure_ok = False
        self.top_level_triggered = False
        self.bottom_level_triggered = False
        self.pump_status = False
        self.fault_detected = False
        self.op_mode = False

        self.data = {
            "station_id": station_id,
            "pressure_switch": False,
            "top_level": False,
            "bottom_level": False,
            "pump_status": False,
            "fault_detected": False,
            "op_mode": False,
            "soft_manual": False,
            "is_next_station_online": False,
            "last_time_of next_station": None
        }
        
        # Network state tracking
        self.mqtt_connected = False
        self.next_station_online = False
        self.last_status_update = {}
        self.station_status = {}
        self.no_updates_timeout = 30
        self.number_of_stations_in_series = 2
        
        # Initialize communication clients
        self.mqtt_client = mqtt_client.MQTTClient(
            id=f"station_{station_id}",
            broker = broker,
            callback=self.mqtt_callback
        )
        self.serial_client = serial_client.SerialClient(self.serial_callback)
        
        # Local control mode parameters
        self.LOCAL_PUMP_INTERVAL = 2700  # 45 minutes
        self.last_pump_time = 0
        self.local_mode = False
        self.toggle = True
        
        # Start monitoring thread
        self.running = True
        self.monitor_loop()
        self.monitor_thread = threading.Thread(target=self.monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def mqtt_callback(self, data: Dict):
        """Handle incoming MQTT messages."""

        try:
            station_id = data.get("station_id")
            if self.data["station_id"] + 1 == station_id:
                self.data["is_next_station_online"] = True
                self.data["last_time_of_next_station"] = time.time()

                if data.get("op_mode", False):
                    # Take action based on status of next pump station
                    self.handle_network_mode(data)
                else:
                    self.handle_local_mode()

            elif self.data["station_id"] == station_id and not self.data["is_next_station_online"]:
                self.handle_local_mode()
        except Exception as e:
            self.handle_local_mode()  # Fallback to local mode on error

    def serial_callback(self, data: Dict):
        """Handle incoming serial data from Arduino."""
        try:
            self.update_station_state(data)

            if self.mqtt_client.is_connected():
                self.mqtt_client.send(self.data)  # Forward to MQTT
            else:
                self.handle_local_mode()
        except Exception as e:
            self.handle_local_mode()  # Fallback to local mode on error

    def update_station_state(self, data: Dict):
        """Update internal state based on Arduino data."""
        self.pressure_ok = data.get("pressure_switch", False)
        self.top_level_triggered = data.get("top_level", False)
        self.bottom_level_triggered = data.get("bottom_level", False)
        self.pump_status = data.get("pump_status", False)
        self.fault_detected = data.get("fault", False)
        self.op_mode = data.get("op_mode", False)

        self.data["presssure_switch"] = data.get("pressure_switch", False)
        self.data["top_level"] = data.get("top_level", False)
        self.data["bottom_level"] = data.get("bottom_level", False)
        self.data["pump_status"] = data.get("pump_status", False)
        self.data["fault_detected"] = data.get("fault", False)
        self.data["op_mode"] = data.get("op_mode", False)

        print(f"pump status {self.pump_status}")
        print(f"fault status {self.fault_detected}")
        print(f"pressure status {self.pressure_ok}")
        print(f"top float status {self.top_level_triggered}")
        print(f"bottom float status {self.bottom_level_triggered}")
        print(f"op_mode status {self.op_mode}")

    def should_monitor_station(self, station_id: int) -> bool:
        """Determine if we should monitor this station based on our station ID."""
        if self.station_id == 1:
            return station_id == 2
        elif self.station_id == 2:
            return station_id == 3
        return False

    def handle_network_mode(self, data: Dict):
        """Process status updates from the next station in the chain."""
        if self.station_id == 1:  # Station 1 monitors Station 2's bottom level
            if not self.pressure_ok:
                self.stop_pump()
                print("pressure not ok")
            elif not data.get("bottom_level", True) and not data.get("top_level", True) and not self.fault_detected:
                self.start_pump()
                print("start pump")
            elif data.get("bottom_level", False) and data.get("top_level", False):
                self.stop_pump()
                print("stop pump")


        elif self.station_id == 2:  # Station 2 monitors Station 3's levels
            if not self.bottom_level_triggered and not self.top_level_triggered:
                self.stop_pump()
                print("stop pump")

            elif not data.get("bottom_level", True) and not data.get("top_level", True) and not self.fault_detected:
                self.start_pump()
                print("start pump")
            elif data.get("bottom_level", False) and data.get("top_level", False):
                self.stop_pump()
                print("stop pump")


        elif self.station_id == 3:
            pass

    def start_pump(self):
        """Start the pump if conditions allow."""
        if not self.control_pump:
            return
            
        if self.station_id == 1:
            if self.pressure_ok and not self.fault_detected:
                self.send_pump_command(True)
        else:
            if not self.top_level_triggered and not self.fault_detected:
                self.send_pump_command(True)

    def stop_pump(self):
        """Stop the pump."""
        if self.control_pump:
            self.send_pump_command(False)

    def send_pump_command(self, state: bool):
        """Send pump control command to Arduino."""
        command = {"pump_control": state}
        self.serial_client.send(command)

    def is_connected(self):
        return self.mqtt_client.is_connected()


    def handle_local_mode(self):
        """Manage pump operation in local control mode."""
        print("handle local mode start")
        current_time = time.time()
        
        if self.station_id == 1:
            print("station 1 ............")
            # Station 1: Use pressure switch and timing
            if not self.fault_detected:
                if self.pressure_ok:
                    print("pressure ok")
                    if current_time - self.last_pump_time >= self.LOCAL_PUMP_INTERVAL:
                        self.last_pump_time = current_time
                        if self.toggle:
                            self.start_pump()
                            print("start pump on station 1 local")
                            self.toggle = not self.toggle
                        else:
                            self.stop_pump()
                            print("stop pump on station 1 local")
                            self.toggle = not self.toggle

                else:
                    self.stop_pump()
                    print("stop pump on station 1 local")
                
        elif self.station_id == 2:
            print("station 2 ...........")
            # Station 2: Use local tank levels
            if not self.fault_detected:
                if self.top_level_triggered and self.bottom_level_triggered:
                    print("station 2 start pump local")
                    self.start_pump()
                elif not self.top_level_triggered and not self.bottom_level_triggered:
                    print("station 2 stop pump local")
                    self.stop_pump()

        elif self.station_id == 3:
            # station 3 doesnt control its motor
            print("station 3 ...........")
            pass 

    def monitor_loop(self):
        """Main monitoring loop to handle mode switching and status checks."""
        while self.running:

            if self.data["last_time_of next_station"] != None:
                if time.time() - self.data["last_time_of next_station"] > self.no_updates_timeout:
                    self.data["is_next_station_online"] = False

            mode = ""
            if not self.data["is_next_station_online"]:
                mode = "local"
            else:
                mode = "network"
            print(f"Station {self.station_id} switching to {mode} mode")

            time.sleep(1)

    def cleanup(self):
        """Clean up resources when shutting down."""
        self.running = False
        if self.monitor_thread.is_alive():
            self.monitor_thread.join()
        self.mqtt_client.cleanup()
        self.serial_client.stop()
