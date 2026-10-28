from enum import Enum
import json
import numpy as np
from threading import Thread, Lock, Event

from multimethod import multimethod
from random_word import RandomWords

from .Sensors import Sensor, SensorInterfaceType
from IO.MQTT_Server import MQTTServer

class State(Enum):
    OFF = 0
    STARTING_UP = 1
    INITAILISING_SENSORS = 2
    MOVING = 3
    AWAITING_ORDERS = 4
    ERROR = -1

class SUBSCRIPTIONS(Enum):
    CONTROLLER_MOVE_TOPIC = 'Robot/controller/Move'
    CONTROLLER_COMMAND_TOPIC = 'Robot/command'

class PUBLICATIONS(Enum):
    RESPONSE_TOPIC = 'Robot/response'
    SENSOR_VALUE_PUB_TOPIC = 'Robot/Sensors'

class Robot:
    def __init__(self, id:str = None):
        if id is None:
            rand_wrd = RandomWords()
            self.robot_id = " ".join([rand_wrd.get_random_word(), rand_wrd.get_random_word()]).lstrip()
        else:
            self.robot_id = id

        self.sensor_set = set()
        self.state = State.OFF
        self.pos = np.array([0,0])
        self.shutdown_event = Event()
        self.MQTT_service = MQTTServer(self.robot_id)
        self.MQTT_command_thread = None

        self.thread_lock = Lock()

    @multimethod
    def attach_sensor(self, sensor:Sensor):
        self.sensor_set.add(sensor)
    @multimethod
    def attach_sensor(self, sensors:list[Sensor]):
        for _sensor in sensors:
            self.sensor_set.add(_sensor)

    def initialise(self):
        print(f"Starting Robot : {self.robot_id}")
        self.state = State.STARTING_UP
        self.MQTT_service.connect()

        for topic in SUBSCRIPTIONS:
            self.MQTT_service.subscribe(topic=topic.value)

        self.init_sensors()

        self.MQTT_command_thread = Thread(target=self.subscription_thread, args=(self.shutdown_event,))
        self.MQTT_command_thread.start()

        self.state = State.AWAITING_ORDERS


    def subscription_thread(self, shutdown_event:Event):
        while not shutdown_event.is_set():
            try:
                topic, command = self.MQTT_service.read_message(timeout=0.2)
            except TimeoutError:
                continue
            except UnicodeDecodeError:
                print("Ignoring command with invalid UTF-8 encoding.")
                continue
            if shutdown_event.is_set():
                break

            if topic.endswith('/' + SUBSCRIPTIONS.CONTROLLER_COMMAND_TOPIC.value):
                self.handle_sensor_command(command)

            elif topic.endswith('/' + SUBSCRIPTIONS.CONTROLLER_MOVE_TOPIC.value):
                self.handle_move_command(command)

    def handle_sensor_command(self, command: str):
        command_parts = command.strip().split(maxsplit=1)
        if len(command_parts) == 2 and command_parts[0].lower() == "get_sensor":
            sensor_selection = command_parts[1]

            if sensor_selection.lower() == "all":
                print("Listing ALL")
                response = {"All Sensors": " ".join(self.get_all_sensor_names).lstrip()}

            else:
                sensor = self.get_sensor_by_name(sensor_selection)
                if sensor is None:
                    response = {"error": f"Unknown sensor: {sensor_selection}"}
                else:
                    response = {"sensor": sensor_selection, "value": sensor.read_sensor_value()}

        else:
            response = {"error": "Unsupported command. Use: query <sensor_name>"}
        self.MQTT_service.publish(PUBLICATIONS.RESPONSE_TOPIC.value, json.dumps(response))

    def handle_move_command(self, command: str):
        try:
            prefix, coordinates = command.strip().split("MOVE TO", 1)
            if prefix.strip():
                raise ValueError("Expected MOVE TO X,Y")
            x, y = map(int, coordinates.split(','))
        except ValueError:
            print(f"Ignoring invalid Move command: {command!r}. Use MOVE TO X,Y with integers.")
            return

        with self.thread_lock:
            self.move(x,y)

    def init_sensors(self, ):
        self.state = State.INITAILISING_SENSORS
        for _sensor in self.sensor_set:
            _sensor.initialise(self.MQTT_service, PUBLICATIONS.SENSOR_VALUE_PUB_TOPIC.value)

    def get_sensor_by_name(self, name:str) -> Sensor:
        _search_set = {sensor for sensor in self.sensor_set if sensor.name == name}
        if len(_search_set)>0:
            return _search_set.pop()

    def get_sensors_by_interface(self, interface:SensorInterfaceType) -> Sensor:
        _search_set = {sensor for sensor in self.sensor_set if sensor.interface == interface}
        return _search_set

    def move(self, x, y):
        # WIll need to make this a thread so that while the program runs,
        # the robot moves
        self.state = State.MOVING
        delta = np.array([x,y]) - self.pos
        self.pos += delta
        print(f"Robot moved to: {self.pos}")

    def shutdown(self):
        self.shutdown_event.set()
        if self.MQTT_command_thread is not None:
            self.MQTT_command_thread.join()
        self.MQTT_service.disconnect()
        for sensor in self.sensor_set:
            sensor.shutdown()
        self.state = State.OFF

    @property
    def get_pos(self):
        return self.pos

    @property
    def get_all_sensor_names(self):
        return [sensor.name for sensor in self.sensor_set]