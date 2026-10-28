from Robot.Sensors import Sensor, SensorInterfaceType
from Robot.Robot import Robot # My best work yet...
from MQTT_Server import MQTTServer
import json

# Configure the robot to have a bucnh of sensors
light_sensor = Sensor("light_sensor", SensorInterfaceType.I2C, frequency_hz=15)
temperature_sensor = Sensor("temperature_sensor", SensorInterfaceType.SPI, frequency_hz=20)
distance_sensor = Sensor("distance_sensor", SensorInterfaceType.GPIO, frequency_hz=5)
pressure_sensor = Sensor("pressure_sensor", SensorInterfaceType.UART, frequency_hz=10)
humidity_sensor = Sensor("humidity_sensor", SensorInterfaceType.ANALOG, frequency_hz=10)

puck_robot = Robot()
puck_robot.attach_sensor([light_sensor, temperature_sensor, distance_sensor, pressure_sensor, humidity_sensor])
puck_robot.initialise()

server = MQTTServer(client_id="ROBOT")
server_connected = False

try:
    server.connect()
    server_connected = True
    server.subscribe("Robot/command")
    print("Waiting for commands on Robot/command (for example: query light_sensor)")

    while True:
        topic, command = server.read_message()
        command_parts = command.strip().split(maxsplit=1)

        if len(command_parts) == 2 and command_parts[0].lower() == "query":
            sensor_name = command_parts[1]
            sensor = puck_robot.get_sensor_by_name(sensor_name)
            if sensor is None:
                response = {"error": f"Unknown sensor: {sensor_name}"}
            else:
                print(f"Response: {sensor.read_sensor_value()}")
                response = {
                    "sensor": sensor_name,
                    "value": sensor.read_sensor_value(),
                }
        else:
            response = {"error": "Unsupported command. Use: query <sensor_name>"}

        server.publish("Robot/response", json.dumps(response))
        print(f"Command received on {topic}: {command}")

except KeyboardInterrupt:
    pass
finally:
    try:
        if server_connected:
            server.disconnect()
    finally:
        puck_robot.shutdown()
