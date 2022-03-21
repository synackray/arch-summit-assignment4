#!/usr/bin/env python3
"""MQTT Client for Group Assignment 4"""

import argparse
import os
import json

from paho.mqtt import client as mqtt_client

from logger import log


def parse_args() -> argparse.Namespace:
    """Handle argument definitions and parsing of user input"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-b', '--broker', type=str, required=True,
        help="MQTT Broker to connect to (IP or Hostname)."
        )
    parser.add_argument(
        '-p', '--port', type=int, default=1883, metavar=1883,
        help="MQTT Broker port to connect to. (default: 1883)"
        )
    parser.add_argument(
        '-u', '--user', type=str, metavar='user',
        help="Username to authenticate to MQTT broker."
        )
    parser.add_argument(
        '-P', '--password', type=str, metavar='secretpass',
        help="Password of username to authenticate to MQTT broker."
        )
    parser.add_argument(
        '-l', '--labs', type=int, default=10, metavar=10,
        help="Quantity of labs to setup and monitor. (default: 10)"
        )
    parser.add_argument(
        '-v', '--verbose', action='store_true',
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
        self.broker =  os.getenv('MQTT_BROKER', '')
        self.port = int(os.getenv('MQTT_PORT', 1883))
        self.user =  os.getenv('MQTT_USER', '')
        self.password =  os.getenv('MQTT_PASSWORD', '')
        self.port = int(os.getenv('MQTT_LABS', 10))
        self.verbose = bool(os.getenv('VERBOSE', False))


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
    """Format a Home Assistant discovery payload for MQTT devices

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

def format_config(discovery_msg: str) -> dict:
    """Format a Home Assistant discovery config topic

    :param discovery_msg: Discovery message from format_discovery
    :returns: Dict of formatted Home Assistant config topic
    """
    topic = '/'.join(discovery_msg['state_topic'].split('/')[:-1])
    return f'{topic}/config'


def template_config_motion(name: str) -> dict:
    """Generate the config for a motion sensor

    :param name: Name of the motion sensor [alphanumeric]
    :returns: HA compatible motion sensor config
    """
    return {
        'name': name,
        'device_class': 'motion',
        'state_topic': f'homeassistant/binary_sensor/{name}/state'
        }


def template_config_temperature(name: str) -> dict:
    """Generate the config for a temperature sensor

    :param name: Name of the temperature sensor [alphanumeric]
    :returns: HA compatible temperature sensor config
    """
    return {
        'name': name,
        'device_class': 'temperature',
        'state_topic': f'homeassistant/sensor/{name}/state',
        # Do we need to define unit of measurement?
        'value_template': '{{ value_json.temperature }}'
        }


def template_config_humidity(name: str) -> dict:
    """Generate the config for a humidity sensor

    :param name: Name of the humidity sensor [alphanumeric]
    :returns: HA compatible humidity sensor config
    """
    return {
        'name': name,
        'unique_id': f'{name}_humidity',
        'device_class': 'humidity',
        'state_topic': f'homeassistant/sensor/{name}/state',
        'unit_of_measurement': '%',
        'value_template': '{{ value_json.humidity }}'
        }


def template_config_light(name: str) -> dict:
    """Generate the config for a light

    :param name: Name of the light [alphanumeric]
    :returns: HA compatible light config
    """
    return {
        'name': name,
        'unique_id': f'{name}_light',
        'command_topic': f'homeassistant/light/{name}/set',
        'state_topic': f'homeassistant/light/{name}/state',
        'schema': 'json',
        'brightness': True
        }


def template_config_climate(name: str) -> dict:
    """Generate the config for a climate controller

    :param name: Name of the controller [alphanumeric]
    :returns: HA compatible climate config
    """
    return {
        'name': name,
        'mode_cmd_t': f'homeassistant/climate/{name}/thermostatModeCmd',
        'mode_stat_t': f'homeassistant/climate/{name}/state',
        'mode_stat_tpl': '',
        'avty_t': f'homeassistant/climate/{name}/available',
        'pl_avail': 'online',
        'pl_not_avail': 'offline',
        'temp_cmd_t': f'homeassistant/climate/{name}/targetTempCmd',
        'temp_stat_t': f'homeassistant/climate/{name}/state',
        # The naming is inconsistent, but I'm going to try anyways
        # as doing so lets me keep the topic lookup function
        'state_topic': f'homeassistant/climate/{name}/state',
        'temp_stat_tpl': '',
        'curr_temp_t': f'homeassistant/climate/{name}/state',
        'curr_temp_tpl': '',
        'min_temp': '60',
        'max_temp': '110',
        'temp_step': '1.0',
        'modes': ['off', 'heat']
        }


def main() -> None:
    """Main function ran when the script is called directly"""
    # Determine whether we're running in a container or by a user
    args = EnvironmentArgs() if os.getenv("MQTT_BROKER", "") else parse_args()
    if args.verbose:
        log.setLevel('DEBUG')
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
        topic = f'summit/lab4/group{lab}/completed'
        payload = 'False'
        publish(client, topic, payload)
        subscribe(client, topic)
    # Create a test device discoverable in Home Assistant
    configs = [
        template_config_motion(name='bedroom-motion1'),
        template_config_temperature(name='bedroom-temp1'),
        template_config_humidity(name='bedroom-temp1'),
        template_config_light(name='bedroom-light1'),
        template_config_climate(name='bedroom-heater1')
        ]
    for config in configs:
        topic = format_config(config)
        publish(client, topic, json.dumps(config))
    # Have the client stay alive forever
    client.loop_forever()


if __name__ == '__main__':
    main()