from IO.MQTT_Server import MQTTServer
import math
from time import sleep
from threading import Event, Thread

class Robot:
    def __init__(self):
        self.server = MQTTServer(client_id='ROBOT')
        self.server.connect()
        self.stop_event = Event()

    def normal_equation(self, x):
        return math.exp(-((x-10)**2)/25)*100//1

    def distance_equation(self, x):
        return 100 - x

    def temperature_equation(self, x):
        return 20 + x / 10

    def publish_sensor(self, out_topic, sensor_function):
        while not self.stop_event.is_set():
            for i in range(0, 60):
                if self.stop_event.is_set():
                    break
                payload = sensor_function(i)
                self.server.publish(topic=out_topic, payload=payload)
                self.stop_event.wait(0.5)

    def create_sensor_threads(self):
        sensor_threads = [
            Thread(target=self.publish_sensor, args=('Robot/sensor/light', self.normal_equation)),
            Thread(target=self.publish_sensor, args=('Robot/sensor/distance', self.distance_equation)),
            Thread(target=self.publish_sensor, args=('Robot/sensor/temperature', self.temperature_equation)),
        ]

        return sensor_threads

    def initialise_robot(self):
        sensor_threads = self.create_sensor_threads()
        for thread in sensor_threads:
            thread.start()
        try:
            while any(thread.is_alive() for thread in sensor_threads):
                sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop_event.set()
            for thread in sensor_threads:
                thread.join()
            self.server.disconnect()

robot = Robot()
robot.initialise_robot()