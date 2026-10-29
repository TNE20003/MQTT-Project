from enum import Enum

class COMMMANDS(Enum):
    GET_SENSOR = "get_sensor"
    GET_ALL_SENSORS = "get_sensor all"
    MOVE_TO = "MOVE TO"


class SUBSCRIPTIONS(Enum):
    CONTROLLER_MOVE_TOPIC = 'Robot/controller/Move'
    CONTROLLER_COMMAND_TOPIC = 'Robot/command'

class PUBLICATIONS(Enum):
    RESPONSE_TOPIC = 'Robot/response'
    SENSOR_VALUE_PUB_TOPIC = 'Robot/Sensors'