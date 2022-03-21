#!/usr/bin/env python3
"""MQTT Client for Group Assignment 4"""

import argparse
import os
import json
import random
import time

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
        self.labs = int(os.getenv('MQTT_LABS', 10))
        self.verbose = bool(os.getenv('VERBOSE', False))


def connect_mqtt(
        broker: str, port: int, user: str = '',
        password: str = '') -> mqtt_client:
    def on_connect(client, userdata, flags, rc):
        if not rc:
            log.info("Connected to %s.", broker)
        else:
            raise ConnectionError(
                log.error(
                    "Failed to connect to %s, return code %d\n", broker, rc)
                    )
    client = mqtt_client.Client(clean_session=True)
    client.username_pw_set(user, password)
    client.on_connect = on_connect
    log.info("Connecting to MQTT Broker '%s' on port '%s'.", broker, port)
    client.connect(broker, port, keepalive=60)
    return client


def publish(client: mqtt_client, topic: str, payload: str,
        retain: bool = False) -> None:
    """Publish a topic to the MQTT Broker

    :param client: MQTT client session
    :param topic: Topic path
    :param payload: Payload topic is set to'
    :param retain: Determine whether to retain the message
    """
    result = client.publish(topic, payload, retain=retain)
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


def get_parent_topic(config_template: str) -> dict:
    """Evaluate a device state topic string and get its parent topic

    :param config_template: Generated config template for a device
    :returns: Dict of formatted Home Assistant parent topic
    """
    topic = '/'.join(config_template['state_topic'].split('/')[:-1])
    return f'{topic}'


def template_config_motion(name: str) -> dict:
    """Generate the config for a motion sensor

    :param name: Name of the motion sensor [alphanumeric]
    :returns: HA compatible motion sensor config
    """
    return {
        'name': name,
        'unique_id': f'{name}_motion',
        'device_class': 'motion',
        'state_topic': f'homeassistant/binary_sensor/{name}/state'
        }


def template_config_temperature(name: str) -> dict:
    """Generate the config for a temperature sensor

    :param name: Name of the temperature sensor [alphanumeric]
    :returns: HA compatible temperature sensor config
    """
    return {
        'name': f'{name} Temperature',
        'device_class': 'temperature',
        'state_topic': f'homeassistant/sensor/{name}T/state',
        'unit_of_measurement': 'F',
        'value_template': '{{ value_json.temperature }}'
        }


def template_config_humidity(name: str) -> dict:
    """Generate the config for a humidity sensor

    :param name: Name of the humidity sensor [alphanumeric]
    :returns: HA compatible humidity sensor config
    """
    return {
        'name': f'{name} Humidity',
        'device_class': 'humidity',
        'state_topic': f'homeassistant/sensor/{name}H/state',
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


def template_config_switch(name: str) -> dict:
    """Generate the config for a switch

    :param name: Name of the switch [alphanumeric]
    :returns: HA compatible switch config
    """
    return {
        'name': name,
        'unique_id': f'{name}_switch',
        'command_topic': f'homeassistant/switch/{name}/set',
        'state_topic': f'homeassistant/switch/{name}/state',
        'value_template': '{{ value_json.state }}'
        }


def template_config_climate(name: str) -> dict:
    """Generate the config for a climate controller

    :param name: Name of the controller [alphanumeric]
    :returns: HA compatible climate config
    """
    return {
        'name': name,
        'unique_id': f'{name}_climate',
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
        'temp_step': '0.5',
        'modes': ['off', 'heat']
        }


def random_state_binary_sensor() -> str:
    """Generate a random binary sensor state

    :returns: HA compatible MQTT state payload
    """
    states = ["ON", "OFF"]
    result = {'state': random.choice(states)}
    return json.dumps(result)


def random_state_sensor() -> str:
    """Generate a random sensor state

    :returns: HA compatible MQTT state payload
    """
    # I'm being a bit lazy and using the same state generator for both the
    # temperature and humidity sensors assuming there aren't any other
    # sensors defined that need different payloads.
    # Don't do this in production. :^)
    result = {
        'temperature': f'{random.uniform(60.0, 110.0):.1f}',
        'humidity': f'{random.uniform(0.0, 100.0):.0f}',
        }
    return json.dumps(result)


def random_state_switch() -> str:
    """Generate a random switch state

    :returns: HA compatible MQTT state payload
    """
    states = ["ON", "OFF"]
    result = {'state': random.choice(states)}
    return json.dumps(result)


def random_state_light() -> str:
    """Generate a random light state

    :returns: HA compatible MQTT state payload
    """
    states = ["ON", "OFF"]
    result = {
        'state': random.choice(states),
        'brightness': random.randint(0, 255),
        }
    return json.dumps(result)

def random_state_climate() -> str:
    """Generate a random light state

    :returns: HA compatible MQTT state payload
    """
    states = ["off", "heat"]
    result = {
        'mode': random.choice(states),
        'target_temp': f'{random.uniform(60.0, 110.0):.2f}',
        'current_temp': f'{random.uniform(60.0, 110.0):.2f}',
        }
    return json.dumps(result)


def publish_random_state(client: mqtt_client, topic: str) -> None:
    """Publish an MQTT message to :param topic: with random state

    :param client: MQTT client session
    :param topic: Parent device topic
    """
    state_topic = f'{topic}/state'
    # Extract the component type
    component = topic.split('/')[1]
    # Generate a random state based on the component type
    # I really dislike accessing globals. Perhaps the better way to do
    # this would be creating a template class.. but this is throw away
    state = globals()[f'random_state_{component}']()
    # Do an ugly fix for motion sensors
    if 'binary_sensor' in state_topic and 'motion' in state_topic:
        state = json.loads(state)
        state = state['state']
    publish(client, state_topic, state, retain=True)


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
    # TODO - Create binary sensory with "WINNERS!"
    # TODO - Maybe use some sort of alarm pin?
    # Create a set of test devices in Home Assistant
    configs = [
        # Bedroom
        template_config_motion(name='bedroom-motion1'),
        template_config_temperature(name='bedroom-temp1'),
        template_config_humidity(name='bedroom-temp1'),
        template_config_light(name='bedroom-light1'),
        template_config_light(name='bedroom-lamp1'),
        template_config_light(name='bedroom-lamp2'),
        # This isn't working the way I'd hope it would
        # Disabling it for now
        # template_config_climate(name='bedroom-heater1')
        # Office
        template_config_motion(name='office-motion1'),
        template_config_temperature(name='office-temp1'),
        template_config_humidity(name='office-temp1'),
        template_config_light(name='bedroom-light1'),
        template_config_light(name='do-not-disturb-light1'),
        # Living Room
        template_config_motion(name='lroom-motion1'),
        template_config_temperature(name='lroom-temp1'),
        template_config_humidity(name='lroom-temp1'),
        template_config_light(name='lroom-light1'),
        template_config_switch(name='lroom-tv1'),
        # Garage
        template_config_motion(name='garage-motion1'),
        template_config_temperature(name='garage-freezer-temp1'),
        template_config_light(name='garage-light1'),
        template_config_switch(name='garage-tv1'),
        # Garden
        template_config_motion(name='garden-motion1'),
        template_config_light(name='garden-path-lights1'),
        template_config_switch(name='garden-founain1'),
        ]
    topics = []
    # Publish the device config topics
    for config in configs:
        topic = get_parent_topic(config)
        # Store the parent topic so we can use it later
        topics.append(topic)
        config_topic = f'{topic}/config'
        publish(client, config_topic, json.dumps(config), retain=True)
    # Publish initial device states
    for topic in topics:
        # Send the initial data
        publish_random_state(client, topic)
        # Normalize it with a change
        time.sleep(5)
        publish_random_state(client, topic)
    # Update topics from time to time
    while True:
        topic = random.choice(topics)
        publish_random_state(client, topic)
        time.sleep(5)
    # Have the client stay alive forever
    # client.loop_forever()


if __name__ == '__main__':
    main()