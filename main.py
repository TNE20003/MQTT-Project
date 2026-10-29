from Robot.Sensors import Sensor, SensorInterfaceType
from Robot.Robot import Robot # My best work yet...
from Robot.Controller import Controller

from threading import Thread

from IO.UI import MQTTUI
import tkinter as tk


def run_ui():
    window = tk.Tk()
    MQTTUI(window)
    window.mainloop()

# Configure the robot to have a bucnh of sensors
light_sensor = Sensor("light_sensor", SensorInterfaceType.I2C, frequency_hz=15)
temperature_sensor = Sensor("temperature_sensor", SensorInterfaceType.SPI, frequency_hz=20)
distance_sensor = Sensor("distance_sensor", SensorInterfaceType.GPIO, frequency_hz=5)
pressure_sensor = Sensor("pressure_sensor", SensorInterfaceType.UART, frequency_hz=10)
humidity_sensor = Sensor("humidity_sensor", SensorInterfaceType.ANALOG, frequency_hz=10)

puck_robot = Robot()
puck_robot.attach_sensor([light_sensor, temperature_sensor, distance_sensor, pressure_sensor, humidity_sensor])


controller = Controller(move_target=(1,0))

Thread(target=run_ui).start()

try:
    puck_robot.initialise()
    controller.run()
    # MQTTUI()

    puck_robot.shutdown_event.wait()
except KeyboardInterrupt:
    pass
finally:
    puck_robot.shutdown()
# Basically move the robot around randomly based on the readings (Where it always travels in the direction of the most humid and lowest light)