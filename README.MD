Create python venv environment

pip install paho-mqtt pyserial


before running main.py
in main.py choosinge the station configuration
choose the internal ip address of the raspberry pi at station 1 to be 
10.10.0.248

the ip adress att he other stations should be the external ip adress of station 1 since its hosting the mqtt broker
10.10.10.6

in pumpstation.py
change the value in seconds for how long pump at station 1 should alternate ON and OFF
self.LOCAL_PUMP_INTERVAL = 2700  # 45 minutes
