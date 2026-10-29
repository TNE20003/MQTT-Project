from enum import Enum
import json
import numpy as np
from threading import Thread, Lock, Event

from multimethod import multimethod
from random_word import RandomWords

from .Sensors import Sensor, SensorInterfaceType
from IO.MQTT_Server import MQTTServer
from IO.MQTT_Topics import COMMMANDS, SUBSCRIPTIONS, PUBLICATIONS

class State(Enum):
    OFF = 0
    STARTING_UP = 1
    INITAILISING_SENSORS = 2
    MOVING = 3
    AWAITING_ORDERS = 4
    ERROR = -1


class Robot:
    def __init__(self, name:str = None):
        """ This is the robot which is to be controlled by the controller object. Sensors could be added to it and it can be moved around.

        Args:
            name (str, optional): The name of the robot. If no name is provided, a name is provided using two randomly generated words. Defaults to None.
        """
        if name is None:
            rand_wrd = RandomWords()
            self.robot_id = " ".join([rand_wrd.get_random_word(), rand_wrd.get_random_word()]).lstrip()
        else:
            self.robot_id = name

        self.sensor_set = set()
        self.state = State.OFF
        self.pos = np.array([0,0])
        self.shutdown_event = Event()
        self.MQTT_service = MQTTServer(self.robot_id)
        self.MQTT_command_thread = None
        self.MQTT_command_thread = Thread(target=self.subscription_thread, args=(self.shutdown_event,))
        self.thread_lock = Lock()

    @multimethod
    def attach_sensor(self, sensor:Sensor):
        """
        Adds one sensor to the robot

        Args:
            sensor (Sensor): The sensor to be added
        """
        self.sensor_set.add(sensor)

    @multimethod
    def attach_sensor(self, sensors:list[Sensor]):
        """
        Adds a list of sensors to the robot

        Args:
            sensors (list[Sensor]): A list of sensors to be added
        """
        for _sensor in sensors:
            self.sensor_set.add(_sensor)

    def initialise(self):
        """
        Initialises the robot where it makes the necessary subscriptions and begins the relevant publications.
        In this state, the robot also initialises all connected sensors and starts publishing their the values onto the MQTT server.
        """
        print(f"Starting Robot : {self.robot_id}")
        self.state = State.STARTING_UP
        self.MQTT_service.connect()

        for topic in SUBSCRIPTIONS:
            self.MQTT_service.subscribe(topic=topic.value)

        self.init_sensors()
        self.MQTT_command_thread.start()
        self.state = State.AWAITING_ORDERS


    def subscription_thread(self, shutdown_event:Event):
        """
        This thread is spun on with the initialisation of the robot and works to ensure that all requests to the robot
        are handled.

        Args:
            shutdown_event (Event): Enables graceful shutdown of the thread
        """
        while not shutdown_event.is_set():
            try:
                topic, command = self.MQTT_service.read_message(timeout=0.2)
            except TimeoutError as te:
                # print(f"Unable to process read message: {te}")
                continue

            if shutdown_event.is_set():
                break

            if topic.endswith('/' + SUBSCRIPTIONS.CONTROLLER_COMMAND_TOPIC.value):
                self.handle_sensor_command(command)

            elif topic.endswith('/' + SUBSCRIPTIONS.CONTROLLER_MOVE_TOPIC.value):
                self.handle_move_command(command)

    def handle_sensor_command(self, command: str):
        """
        This function handles commands to do with transmitting and/or relaying infromation to relevant publishers.

        Args:
            command (str): The incoming command/request
        """
        command_parts = command.strip().split(maxsplit=1)
        if len(command_parts) == 2 and command_parts[0].lower() == COMMMANDS.GET_SENSOR.value:
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
            response = {"error": "Unsupported command."}

        self.MQTT_service.publish(PUBLICATIONS.RESPONSE_TOPIC.value, json.dumps(response))


    def handle_move_command(self, command: str):
        """
        This function is the one which handles the motion of the robot upon a request made from the controller

        Args:
            command (str): The movement request

        Raises:
            ValueError: If the move command does not follow the appropriate format
        """
        try:
            prefix, coordinates = command.strip().split(COMMMANDS.MOVE_TO.value, 1)
            if prefix.strip():
                raise ValueError("Expected MOVE TO X,Y")
            x, y = map(int, coordinates.split(','))
        except ValueError:
            print(f"Ignoring invalid Move command: {command!r}. Use MOVE TO X,Y with integers.")
            return

        with self.thread_lock:
            self.move(x,y)

    def init_sensors(self):
        """
        Initialises all sensors attached the robot
        """
        self.state = State.INITAILISING_SENSORS
        for _sensor in self.sensor_set:
            _sensor.initialise(self.MQTT_service, PUBLICATIONS.SENSOR_VALUE_PUB_TOPIC.value)

    def get_sensor_by_name(self, name:str) -> Sensor|None:
        """
        This returns a sensor by name

        Args:
            name (str): The name of requested sensor

        Returns:
            Sensor|None: If sensor is present, it will return the sensor object. Else, it will return None.
        """
        _search_set = {sensor for sensor in self.sensor_set if sensor.name == name}
        if len(_search_set)>0:
            return _search_set.pop()

    def get_sensors_by_interface(self, interface:SensorInterfaceType) -> {Sensor}:
        """
        Searchs attached sensors and returns attached sensors as set

        Returns:
            set([Sensor]): A set of sensor objects that have the required interface
        """
        _search_set = {sensor for sensor in self.sensor_set if sensor.interface == interface}
        return _search_set

    def move(self, x:float, y:float):
        """
        Moves the robot to the desired x,y position

        Args:
            x (float): X Position of the robot in the world
            y (float): Y position of the robot in the world
        """

        self.state = State.MOVING
        delta = np.array([x,y]) - self.pos
        self.pos += delta
        print(f"Robot moved to: {self.pos}")

    def shutdown(self):
        """
        Shuts down the robot and all of its sensors
        """
        self.shutdown_event.set()
        if self.MQTT_command_thread is not None:
            self.MQTT_command_thread.join()
        self.MQTT_service.disconnect()
        for sensor in self.sensor_set:
            sensor.shutdown()
        self.state = State.OFF

    @property
    def get_pos(self):
        """
        The positon of the robot 
        """
        return self.pos

    @property
    def get_all_sensor_names(self):
        """
        Returns a list of the names of the sensors attached to the robot
        """
        return [sensor.name for sensor in self.sensor_set]