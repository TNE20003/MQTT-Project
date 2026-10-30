"""Seek a dark, humid location using local light and humidity measurements."""

import json
import math
from time import monotonic

from IO.MQTT_Server import MQTTServer
from IO.MQTT_Topics import SUBSCRIPTIONS, PUBLICATIONS, COMMMANDS


class Controller:
    def __init__(self, move_target=(1, 0), *, sample_period=1.0,
                 dark_threshold=2.0, humidity_threshold=7.0):
        """Use readings on the simulation's 0-10 scale to search nearby positions.

        move_target sets the first search direction. The robot starts at (0, 0).
        Lower light and higher humidity are equally desirable.
        """
        if len(move_target) != 2 or not all(math.isfinite(v) for v in move_target):
            raise ValueError("move_target must contain two finite coordinates")
        if not math.isfinite(sample_period) or sample_period <= 0:
            raise ValueError("sample_period must be positive and finite")
        self.mqtt_server = MQTTServer(client_id="Controller_node")
        self.move_target = move_target
        self.sample_period = sample_period
        self.dark_threshold = dark_threshold
        self.humidity_threshold = humidity_threshold
        self.sensor_names = []
        self.sensor_topics = {}
        self.position = (0, 0)
        self.samples = {"light_sensor": [], "humidity_sensor": []}
        self.sample_started = monotonic()
        self.settle_until = self.sample_started
        self.anchor = None
        self.candidates = []
        self.best_position = None
        self.best_score = None
        self.directions = [(1, 0), (0, 1), (-1, 0), (0, -1)]
        if abs(move_target[1]) > abs(move_target[0]):
            first = (0, 1 if move_target[1] >= 0 else -1)
        else:
            first = (1 if move_target[0] >= 0 else -1, 0)
        start = self.directions.index(first)
        self.directions = self.directions[start:] + self.directions[:start]

    def initialise(self, timeout=5.0):
        self.mqtt_server.connect()
        self.mqtt_server.subscribe(PUBLICATIONS.RESPONSE_TOPIC.value)
        self.mqtt_server.publish(SUBSCRIPTIONS.CONTROLLER_COMMAND_TOPIC.value,
                                 COMMMANDS.GET_ALL_SENSORS.value)
        deadline = monotonic() + timeout
        while True:
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise TimeoutError("Timed out waiting for the robot's sensor list")
            topic, payload = self.mqtt_server.read_message(timeout=remaining)
            if not topic.endswith('/' + PUBLICATIONS.RESPONSE_TOPIC.value):
                continue
            try:
                response = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if not isinstance(response, dict) or "All Sensors" not in response:
                continue
            names = response["All Sensors"]
            if isinstance(names, str):
                names = names.split()
            if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
                continue
            self.sensor_names = names
            break

        required = set(self.samples)
        missing = required.difference(self.sensor_names)
        if missing:
            raise ValueError(f"Missing required sensors: {', '.join(sorted(missing))}")
        for name in self.samples:
            topic = f"{PUBLICATIONS.SENSOR_VALUE_PUB_TOPIC.value}/{name}"
            self.sensor_topics[name] = topic
            self.mqtt_server.subscribe(topic)
        self.sample_started = monotonic()

    def handle_message(self, topic: str, payload: str):
        name = next((name for name, path in self.sensor_topics.items()
                     if topic == path or topic.endswith('/' + path)), None)
        if name is None:
            return
        try:
            value = float(payload)
        except (TypeError, ValueError):
            return
        if not math.isfinite(value) or not 0 <= value <= 10:
            return
        now = monotonic()
        if now < self.settle_until:
            return
        self.samples[name].append(value)
        if now - self.sample_started < self.sample_period:
            return
        if not all(self.samples.values()):
            return
        light = sum(self.samples['light_sensor']) / len(self.samples['light_sensor'])
        humidity = sum(self.samples['humidity_sensor']) / len(self.samples['humidity_sensor'])
        self._reset_samples(now)
        if light <= self.dark_threshold and humidity >= self.humidity_threshold:
            # Continue monitoring here; resume searching if conditions deteriorate.
            self.anchor = None
            self.candidates = []
            return
        # Minimise unmet requirements so an already satisfied sensor does not
        # outweigh progress toward the other requirement.
        score = max(0, light - self.dark_threshold) + max(0, self.humidity_threshold - humidity)
        self._search(score)

    def _reset_samples(self, now):
        for readings in self.samples.values():
            readings.clear()
        self.sample_started = now

    def _search(self, score):
        if self.anchor is None:
            self.anchor = self.position
            self.best_position = self.position
            self.best_score = score
            x, y = self.anchor
            self.candidates = [(x + dx, y + dy) for dx, dy in self.directions]
        elif score < self.best_score - 0.05:
            self.best_position = self.position
            self.best_score = score
        if self.candidates:
            self._move(self.candidates.pop(0))
        else:
            # Return to the best measured neighbour before searching around it.
            target = self.best_position
            self.anchor = None
            if target != self.position:
                self._move(target)

    def _move(self, target):
        command = f"{COMMMANDS.MOVE_TO.value} {target[0]},{target[1]}"
        result = self.mqtt_server.publish(SUBSCRIPTIONS.CONTROLLER_MOVE_TOPIC.value, command)
        if result.rc != 0:
            raise RuntimeError(f"Could not publish movement command (code {result.rc})")
        self.position = target
        now = monotonic()
        # Allow in-flight readings from the previous location to drain first.
        self.settle_until = now + 0.25
        self._reset_samples(self.settle_until)

    def run(self):
        try:
            self.initialise()
            while True:
                try:
                    topic, payload = self.mqtt_server.read_message(timeout=0.2)
                except (TimeoutError, UnicodeDecodeError):
                    continue
                self.handle_message(topic, payload)
        except KeyboardInterrupt:
            pass
        finally:
            self.mqtt_server.disconnect()
