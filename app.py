#!/usr/bin/env python3
"""MQTT Client for Group Assignment 4"""

import argparse
import os
import json

from paho.mqtt import client as mqtt_client

from logger import log

topic = "$SYS/broker/uptime"


def parse_args() -> argparse.Namespace:
    """Handle argument definitions and parsing of user input"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-b", "--broker", type=str, required=True,
        help="MQTT Broker to connect to (IP or Hostname)."
        )
    parser.add_argument(
        "-p", "--port", type=int, default=1883, metavar=1883,
        help="MQTT Broker port to connect to. (default: 1883)"
        )
    parser.add_argument(
        "-u", "--user", type=str, metavar="user",
        help="Username to authenticate to MQTT broker."
        )
    parser.add_argument(
        "-P", "--password", type=str, metavar="secretpass",
        help="Password of username to authenticate to MQTT broker."
        )
    parser.add_argument(
        "-l", "--labs", type=int, default=10, metavar=10,
        help="Quantity of labs to setup and monitor. (default: 10)"
        )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable verbose output. Intended for debugging purposes only."
        )
    args = parser.parse_args()
    if (args.user or args.password) and not all((args.user, args.password)):
        parser.error(
            "The following arguments are required when the user or password "
            "is defined: --user, --password"
            )
    return args


class EnvironmentArgs:
    """Collect environment variables and make them keyname callable"""
    def __init__(self):
        self.broker =  os.getenv("MQTT_BROKER", "")
        self.port = int(os.getenv("MQTT_PORT", 1883))
        self.user =  os.getenv("MQTT_USER", "")
        self.password =  os.getenv("MQTT_PASSWORD", "")
        self.port = int(os.getenv("MQTT_LABS", 10))
        self.verbose = bool(os.getenv("VERBOSE", False))


def connect_mqtt(
        broker: str, port: int, user: str = '',
        password: str = '') -> mqtt_client:
    def on_connect(client, userdata, flags, rc):
        if not rc:
            log.info("Connected to %s.", broker)
        else:
            log.error("Failed to connect to %s, return code %d\n", broker, rc)
    client = mqtt_client.Client(clean_session=True)
    client.username_pw_set(user, password)
    client.on_connect = on_connect
    client.connect(broker, port, keepalive=60)
    return client


def publish(client: mqtt_client, topic: str, payload: str) -> None:
    """Publish a topic to the MQTT Broker

    :param client: MQTT client session
    :param topic: Topic path
    :param payload: Payload topic is set to
    """
    result = client.publish(topic, payload)
    # Status of publish event stored in result[0]
    if not result[0]:
        log.info("Set topic '%s' to '%s'.", topic, payload)
    else:
        log.error("Failed to set topic '%s'.", topic)


def subscribe(client: mqtt_client, topic: str) -> None:
    """Subscribe to the requested topic

    :param topics: Topic to subscribe to
    """
    def on_message(client, userdata, msg):
        log.info("Received '%s' from '%s'.", msg.payload.decode(),
            msg.topic)
    client.subscribe(topic)
    log.info("Subscribed to topic(s) '%s'.", topic)
    client.on_message = on_message


def format_discovery(name: str, device_type: str, manufacturer: str,
        model: str) -> dict:
    """Format a Home Assistant discovery message for MQTT devices

    :returns: Dict of formatted Home Assistant discovery message
    """
    return {
        'name': name,
        'command_topic': f'homeassistant/{device_type}/{name}/set',
        'payload_on': 'ON',
        'payload_off': 'OFF',
        'availability_topic': f'homeassistant/{device_type}/{name}/available',
        'state_topic': f'homeassistant/{device_type}/{name}/state',
        'device': {
            'manufacturer': manufacturer,
            'model': model,
            'name': name
            },
        'value_template': '{{ value_json.state }}'
        }


def main() -> None:
    """Main function ran when the script is called directly"""
    # Determine whether we're running in a container or by a user
    args = EnvironmentArgs() if os.getenv("MQTT_BROKER", "") else parse_args()
    if args.verbose:
        log.setLevel("DEBUG")
        log.debug("Log level has been overriden by the --verbose argument.")
    # Initialize the MQTT Client
    client = connect_mqtt(
        broker=args.broker,
        port=args.port,
        user=args.user,
        password=args.password
        )
    # Establish the connection
    client.loop()
    # Publish all of the lab topics
    for lab in range(args.labs):
        topic = f"summit/lab4/group{lab}/completed"
        payload = "False"
        publish(client, topic, payload)
        subscribe(client, topic)
    # Create a test device discoverable in Home Assistant
    switch1 = format_discovery(
        name='bedroom-light1',
        device_type='switch',
        manufacturer='Tractor Supply Company',
        model='TSCWALLSWITCH1'
        )
    topic = '/'.join(switch1['state_topic'].split('/')[:-1])
    publish(client, topic, json.dumps(switch1))
    # Have the client stay alive forever
    client.loop_forever()


if __name__ == '__main__':
    main()