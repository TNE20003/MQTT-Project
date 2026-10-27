from random import randrange
import math
from threading import Thread, Lock, Event
from time import monotonic, sleep
from enum import Enum

class State(Enum):
    UNINITIALISED = 0
    RUNNING = 1
    SHUTDOWN = 2

class Sensor():
    def __init__(self, sensor_name:str, sensor_type:str, running_frequency_hz:float, sigma: int = None, mu:int = None):
        super().__init__()
        self.sensor_name =sensor_name
        self.sensor_type = sensor_type

        self.sigma = randrange(1, int(monotonic()+1000), 1) if sigma is None else sigma
        self.mu = randrange(self.sigma, self.sigma+1000000, 1) if mu is None else mu

        running_period = 1/running_frequency_hz
        self.read_value_lock = Lock()
        self.shutdown_event = Event()

        self.value_generator_thread = Thread(target=self._value_generator, args=(running_period, self.shutdown_event))
        self.time_t:float = 0
        self.sensor_value_at_t:float = 0.0

        self.state = self.state = State.UNINITIALISED

    def _value_generator(self, running_period:float, shutdown_sensor_event:Event):
            def _generate_value(time:float):
                return (1 / (self.sigma * math.sqrt(2 * math.pi))) * math.exp(
                    -0.5 * ((time - self.mu) / self.sigma) ** 2) * running_period**2 + randrange(0,10)

            while not shutdown_sensor_event.is_set():
                if monotonic()%running_period < 0.05:
                    with self.read_value_lock:
                        if self.time_t<0:
                            raise ValueError(f"Time on sensor {self.sensor_name} not initialised correctly")
                        self.sensor_value_at_t = _generate_value(monotonic())

            else:
                print(f"Shutting down sensor: {self.sensor_name}")

    def shutdown_sensor(self):
         self.shutdown_event.set()
         self.state = State.SHUTDOWN
         self.value_generator_thread.join()

    def initialise_sensor(self):
        self.time_t = monotonic()
        self.value_generator_thread.start()
        self.state = State.RUNNING
        print(f"Initialising Sensor: {self.sensor_name}")

    def read_sensor_value(self):
        if self.state == State.RUNNING:
            with self.read_value_lock:
                return self.sensor_value_at_t

    @property
    def type(self):
        return self.sensor_type

    # @property
    # def state(self):
    #     return State(self.state)

    # @state.setter
    # def state(self, value):
    #     self._state = value