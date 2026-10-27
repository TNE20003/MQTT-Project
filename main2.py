from Robot.Sensors import Sensor, SensorInterfaceType
from Robot.Robot import Robot # My best work yet...
from MQTT_Server import MQTTServer
from time import sleep

# Configure the robot to have a bucnh of sensors
light_sensor = Sensor("light_sensor", SensorInterfaceType.I2C, frequency_hz=15)
temperature_sensor = Sensor("temperature_sensor", SensorInterfaceType.SPI, frequency_hz=20)
distance_sensor = Sensor("distance_sensor", SensorInterfaceType.GPIO, frequency_hz=5)
pressure_sensor = Sensor("pressure_sensor", SensorInterfaceType.UART, frequency_hz=10)
humidity_sensor = Sensor("humidity_sensor", SensorInterfaceType.ANALOG, frequency_hz=10)

puck_robot = Robot()
puck_robot.attach_sensor([light_sensor, temperature_sensor, distance_sensor, pressure_sensor, humidity_sensor])
puck_robot.initialise()

while True:
    try:
        print(puck_robot.get_sensor_by_name("light_sensor").read_sensor_value())
        sleep(2/15)
    except KeyboardInterrupt:
        puck_robot.shutdown()
        break
