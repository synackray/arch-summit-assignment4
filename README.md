# Architecture Summit - Assignment 4
An MQTT client that sets topics, monitors them, and then alerts when they change. The script is written in Python and containerized for easy deployment in the lab.

Good luck, and have fun!

# Environment Variables

| Name        | Type | Default Value |
|-------------|------|---------------|
| MQTT_BROKER | str  |               |
| MQTT_PORT   | int  | 1883          |
| MQTT_USER   | str  |               |
| MQTT_PASS   | str  |               |
| MQTT_LABS   | int  | 10            |
| VERBOSE     | bool | False         |