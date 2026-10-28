"""Run from the project root with: python -m Robot.Controller"""

import json
import math
from time import monotonic

from IO.MQTT_Server import MQTTServer
from IO.MQTT_Topics import SUBSCRIPTIONS, PUBLICATIONS


class Controller:
    def __init__(self, move_target=(1, 0)):
        self.mqtt_server = MQTTServer(client_id=f"Controller_node")
        self.move_target = move_target
        self.sensor_names = []
        self.light_topic = None

    def initialise(self, timeout=5.0):
        self.mqtt_server.connect()
        # Subscribe before sending the request so the reply is not missed.
        self.mqtt_server.subscribe(PUBLICATIONS.RESPONSE_TOPIC.value)
        self.mqtt_server.publish(SUBSCRIPTIONS.CONTROLLER_COMMAND_TOPIC.value, "get_sensor all")
        deadline = monotonic() + timeout
        while True:
            # remaining = deadline - monotonic()
            topic, payload = self.mqtt_server.read_message(timeout=timeout)
            if not topic.endswith('/' + PUBLICATIONS.RESPONSE_TOPIC.value):
                continue
            try:
                response = json.loads(payload)
            except json.JSONDecodeError:
                continue

            if "All Sensors" not in response:
                continue
            names = response["All Sensors"]
            # Accept the robot's space-separated string or a JSON list.
            names = names.split()
            self.sensor_names = names
            break

        print(f"Attached sensors: {self.sensor_names}")

        if "light_sensor" not in self.sensor_names:
            raise ValueError("The robot does not have a light_sensor attached")

        self.light_topic = f"{PUBLICATIONS.SENSOR_VALUE_PUB_TOPIC.value}/light_sensor"
        print(f"subscribing to {self.light_topic}")
        self.mqtt_server.subscribe(self.light_topic)

    def handle_message(self, topic, payload):
        if self.light_topic is None or not topic.endswith('/' + self.light_topic):
            return
        try:
            light_value = float(payload)
        except ValueError:
            print(f"Ignoring invalid light reading: {payload!r}")
            return

        if light_value < 5:
            x, y = self.move_target
            command = f"MOVE TO {x},{y}"
            self.mqtt_server.publish(SUBSCRIPTIONS.CONTROLLER_MOVE_TOPIC.value, command)
            print(f"Light value {light_value}: {command}")

    def run(self):
        try:
            self.initialise()
            while True:
                try:
                    topic, payload = self.mqtt_server.read_message(timeout=0.2)
                except TimeoutError:
                    continue
                except UnicodeDecodeError:
                    print("Ignoring a message with invalid UTF-8 encoding")
                    continue
                print(topic)
                self.handle_message(topic, payload)
        except KeyboardInterrupt:
            pass
        finally:
            self.mqtt_server.disconnect()


# if __name__ == "__main__":
#     Controller(move_target=(1, 0)).run()
