from .Sensors import Sensor, SensorInterfaceType
from enum import Enum
import numpy as np
from threading import Event

from multimethod import multimethod
from random_word import RandomWords


class State(Enum):
    OFF = 0
    STARTING_UP = 1
    INITAILISING_SENSORS = 2
    MOVING = 3
    AWAITING_ORDERS = 4
    ERROR = -1

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

    @multimethod
    def attach_sensor(self, sensor:Sensor):
        self.sensor_set.add(sensor)
    @multimethod
    def attach_sensor(self, sensors:list[Sensor]):
        for _sensor in sensors:
            self.sensor_set.add(_sensor)

    def initialise(self):
        print(f"Starting Robot : {self.robot_id}")
        self.init_sensors()
        self.state = State.STARTING_UP

    def init_sensors(self):
        self.state = State.INITAILISING_SENSORS
        for _sensor in self.sensor_set:
            _sensor.initialise()

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

    def shutdown(self):
        for sensor in self.sensor_set:
            sensor.shutdown()
        self.shutdown_event.set()

    @property
    def get_pos(self):
        return self.pos