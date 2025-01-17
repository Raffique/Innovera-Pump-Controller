#include <ArduinoJson.h>

// Pin definitions
const int PUMP_STATUS_PIN = 7;     // Relay sensing if pump is on/off
const int PRESSURE_SWITCH_PIN = 6;  // For station 1 only
const int TOP_LEVEL_PIN = 6;       // For stations 2 & 3
const int BOTTOM_LEVEL_PIN = 5;    // For stations 2 & 3
const int FAULT_PIN = 4;           // Fault detection
const int OP_MODE_PIN = 3;         // Operation mode switch
const int PUMP_CONTROL_PIN = 39;    // Relay to control pump
const int CONNECTED_STATUS_PIN = 40;    // Relay to connected status
const int BUTTON1_PIN = 9;         // Info button 1
const int BUTTON2_PIN = 10;        // Info button 2

// const int PUMP_STATUS_PIN = 7;     // Relay sensing if pump is on/off
// const int PRESSURE_SWITCH_PIN = 6;  // For station 1 only
// const int TOP_LEVEL_PIN = 6;       // For stations 2 & 3
// const int BOTTOM_LEVEL_PIN = 5;    // For stations 2 & 3
// const int FAULT_PIN = 4;           // Fault detection
// const int OP_MODE_PIN = 3;         // Operation mode switch
// const int PUMP_CONTROL_PIN = 8;    // Relay to control pump
// const int CONNECTED_STATUS_PIN = 9;    // Relay to connected status
// const int BUTTON1_PIN = 10;         // Info button 1
// const int BUTTON2_PIN = 11;        // Info button 2

// Timing control
const unsigned long SEND_INTERVAL = 5000;  // Send status every 5 seconds
unsigned long lastSendTime = 0;

// Station configuration
const int STATION_ID = 1;  // Change this for each station (1, 2, or 3)

void setup() {
  // Initialize serial communication
  Serial.begin(115200);
  
  // Configure input pins with internal pullup
  pinMode(PUMP_STATUS_PIN, INPUT_PULLUP);
  pinMode(PRESSURE_SWITCH_PIN, INPUT_PULLUP);
  pinMode(TOP_LEVEL_PIN, INPUT_PULLUP);
  pinMode(BOTTOM_LEVEL_PIN, INPUT_PULLUP);
  pinMode(FAULT_PIN, INPUT_PULLUP);
  pinMode(OP_MODE_PIN, INPUT_PULLUP);
  pinMode(BUTTON1_PIN, INPUT_PULLUP);
  pinMode(BUTTON2_PIN, INPUT_PULLUP);

  pinMode(13, OUTPUT);
  digitalWrite(13, LOW);
  
  // Configure output pin
  pinMode(PUMP_CONTROL_PIN, OUTPUT);
  digitalWrite(PUMP_CONTROL_PIN, LOW);  // Ensure pump starts off
}

void loop() {
  // Check for incoming commands
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    processCommand(command);
  }
  
  // Send status update at regular intervals
  if (millis() - lastSendTime >= SEND_INTERVAL) {
    sendStatus();
    lastSendTime = millis();
  }
}

void sendStatus() {
  // Create JSON status object
  StaticJsonDocument<200> doc;
  
  doc["station_id"] = STATION_ID;
  doc["pump_status"] = !digitalRead(PUMP_STATUS_PIN);  // Inverted due to LOW trigger
  doc["pressure_switch"] = !digitalRead(PRESSURE_SWITCH_PIN);
  doc["top_level"] = !digitalRead(TOP_LEVEL_PIN);
  doc["bottom_level"] = !digitalRead(BOTTOM_LEVEL_PIN);
  doc["fault"] = !digitalRead(FAULT_PIN);
  if (digitalRead(OP_MODE_PIN) == 1) { doc["op_mode"] = true; } else { doc["op_mode"] = false; };
  
  // Serialize JSON to string
  String jsonString;
  serializeJson(doc, jsonString);
  
  // Send over serial
  Serial.println(jsonString);
}

void processCommand(String command) {
  StaticJsonDocument<200> doc;
  DeserializationError error = deserializeJson(doc, command);
  
  if (error) {
    return;
  }
  
  // Process pump control commands
  if (doc.containsKey("pump_control")) {
    bool pumpState = doc["pump_control"];
    digitalWrite(PUMP_CONTROL_PIN, pumpState);
    
  }

  if (doc.containsKey("connected_status")){
    bool connectedStatus = doc["connected_status"];
    digitalWrite(CONNECTED_STATUS_PIN, connectedStatus);
    digitalWrite(13, connectedStatus);
  }
}