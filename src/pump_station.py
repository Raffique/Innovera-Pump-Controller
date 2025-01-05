import mqtt_client
import serial_client
import json
import time
from typing import Optional, Dict
import threading

class PumpStation:
    def __init__(self, station_id: int, control_pump: bool = True, has_tank: bool = True):
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
        
        # Network state tracking
        self.mqtt_connected = False
        self.next_station_online = False
        self.last_status_update = {}
        self.station_status = {}
        self.no_updates_timeout = 30
        
        # Initialize communication clients
        self.mqtt_client = mqtt_client.MQTTClient(
            id=f"station_{station_id}",
            callback=self.mqtt_callback
        )
        self.serial_client = serial_client.SerialClient()
        self.serial_client.on_messages(self.serial_callback)
        
        # Local control mode parameters
        self.LOCAL_PUMP_INTERVAL = 300  # 5 minutes
        self.last_pump_time = 0
        self.local_mode = False
        
        # Start monitoring thread
        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def mqtt_callback(self, data: Dict):
        """Handle incoming MQTT messages."""
        station_id = data.get("station_id")
        if station_id and station_id != self.station_id:
            self.station_status[station_id] = data
            self.last_status_update[station_id] = time.time()
            
            # check if network/local switch is activated
            if not self.op_mode:
                # Check if this is the next station we need to monitor
                if self.should_monitor_station(station_id):
                    if self.check_all_network_nodes_online():
                        self.handle_network_mode(data)
                    else:
                        self.handle_local_mode()

    def serial_callback(self, data: Dict):
        """Handle incoming serial data from Arduino."""
        if data.get("station_id") == self.station_id:
            self.update_station_state(data)
            if self.mqtt_client.is_connected():
                self.mqtt_client.send(data)  # Forward to MQTT
            else:
                if not self.op_mode:
                    self.handle_local_mode()

    def update_station_state(self, data: Dict):
        """Update internal state based on Arduino data."""
        self.pressure_ok = data.get("pressure_switch", False)
        self.top_level_triggered = data.get("top_level", False)
        self.bottom_level_triggered = data.get("bottom_level", False)
        self.pump_status = data.get("pump_status", False)
        self.fault_detected = data.get("fault", False)
        self.op_mode = data.get("op_mode", False)

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
            if data.get("bottom_level", False) and not self.fault_detected:
                self.start_pump()
            else:
                self.stop_pump()
        elif self.station_id == 2:  # Station 2 monitors Station 3's levels
            if data.get("bottom_level", False) and not self.top_level_triggered:
                self.start_pump()
            elif data.get("top_level", True) or self.top_level_triggered:
                self.stop_pump()
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

    def check_all_network_nodes_online(self):
        """Check if we're connected to MQTT and next station is online."""
        # this not only checks if the current station is online but all other stations
        # this needs to be done cuz the system should only work in network mode if all stations are connected
        if not self.is_connected():
            return False

        for key, value in enumerate(self.last_status_update):
            if  time.time() - value < self.no_updates_timeout:
                return False
            
        return True


    def handle_local_mode(self):
        """Manage pump operation in local control mode."""
        current_time = time.time()
        
        if self.station_id == 1:
            # Station 1: Use pressure switch and timing
            if not self.fault_detected:
                if self.pressure_ok:
                    if current_time - self.last_pump_time >= self.LOCAL_PUMP_INTERVAL:
                        self.start_pump()
                        self.last_pump_time = current_time
                else:
                    self.stop_pump()
                
        elif self.station_id == 2:
            # Station 2: Use local tank levels
            if not self.fault_detected:
                if self.top_level_triggered:
                    self.start_pump()
                elif self.bottom_level_triggered:
                    self.stop_pump()

        elif self.station_id == 3:
            # station 3 doesnt control its motor
            pass 

    def monitor_loop(self):
        """Main monitoring loop to handle mode switching and status checks."""
        while self.running:

            if not self.check_all_network_nodes_online():
                self.local_mode = True
            else:
                self.local_mode = False

            print(f"Station {self.station_id} switching to {'local' if self.local_mode else 'network'} mode")
            
            time.sleep(1)

    def cleanup(self):
        """Clean up resources when shutting down."""
        self.running = False
        if self.monitor_thread.is_alive():
            self.monitor_thread.join()
        self.mqtt_client.cleanup()
        self.serial_client.stop()