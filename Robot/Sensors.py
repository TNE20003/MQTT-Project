from random import randrange
import math
from threading import Thread, Lock, Event
from time import monotonic
from enum import Enum
from IO.MQTT_Server import MQTTServer

class State(Enum):
    UNINITIALISED = 0
    RUNNING = 1
    SHUTDOWN = 2

class SensorInterfaceType(Enum):
    GPIO = 1
    UART = 2
    CAN = 3
    I2C = 4
    SPI = 5
    ANALOG = 6
    DIGITAL = 7

class Sensor:
    def __init__(self, sensor_name:str, interface:SensorInterfaceType, frequency_hz:float, sigma: int = None, mu:int = None):
        self.sensor_name =sensor_name
        self.sensor_interface = interface
        self.position_provider = None

        self.sigma = randrange(1, int(monotonic()+1000), 1) if sigma is None else sigma
        self.mu = randrange(self.sigma, self.sigma+1000000, 1) if mu is None else mu

        self.running_period = 1/frequency_hz
        self.read_value_lock = Lock()
        self.shutdown_event = Event()

        self.time_t:float = 0
        self.sensor_value_at_t:float = 0.0

        self.state = self.state = State.UNINITIALISED

    def _value_generator(self, running_period:float, shutdown_sensor_event:Event, MQTT_Service:MQTTServer, Pub_topic:str):
            def _generate_value(time:float):
                if self.position_provider is not None and self.sensor_name in ("light_sensor", "humidity_sensor"):
                    x, y = self.position_provider()
                    # A shared dark, humid region gives movement a measurable effect.
                    distance = math.hypot(x - 6, y - 4)
                    if self.sensor_name == "light_sensor":
                        return min(10.0, 0.5 + distance)
                    return max(0.0, 9.5 - distance)
                return (1 / (self.sigma * math.sqrt(2 * math.pi))) * math.exp(
                    -0.5 * ((time - self.mu) / self.sigma) ** 2) * running_period**2 + randrange(0,10)

            pub_topic = Pub_topic+"/"+self.sensor_name

            while not shutdown_sensor_event.is_set():
                with self.read_value_lock:
                    if self.time_t<0:
                        raise ValueError(f"Time on sensor {self.sensor_name} not initialised correctly")
                    self.sensor_value_at_t = _generate_value(monotonic())
                MQTT_Service.publish(topic=pub_topic, payload=self.sensor_value_at_t)
                shutdown_sensor_event.wait(running_period)
            else:
                print(f"Shutting down sensor: {self.sensor_name}")

    def shutdown(self):
         self.shutdown_event.set()
         self.state = State.SHUTDOWN
         self.value_generator_thread.join()

    def initialise(self, MQTT_service, pub_topic:str):
        self.time_t = monotonic()
        self.value_generator_thread = Thread(target=self._value_generator, args=(self.running_period, self.shutdown_event, MQTT_service, pub_topic,))

        self.value_generator_thread.start()
        self.state = State.RUNNING
        print(f"Initialising Sensor: {self.sensor_name}")

    def read_sensor_value(self):
        if self.state == State.RUNNING:
            with self.read_value_lock:
                return self.sensor_value_at_t

    @property
    def type(self):
        return self.sensor_interface

    @property
    def name(self):
        return self.sensor_name

    @property
    def interface(self):
        return self.sensor_interface

    # @property
    # def state(self):
    #     return State(self.state)

    # @state.setter
    # def state(self, value):
    #     self._state = value
