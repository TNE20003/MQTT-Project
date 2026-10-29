import paho.mqtt.client as mqtt
from queue import Empty, Queue
from threading import Lock
from time import monotonic


class MQTTServer:
    def __init__(self, client_id:str):
        """
        This class is in charge of handling all MQTT communications across all components in this project

        Args:
            client_id (str): The name of the client using this class
        """
        self.mqtt_broker = 'rule28.i4t.swin.edu.au'
        self.client = mqtt.Client(client_id=client_id, clean_session=True)
        self.username_password = "{103218929}"
        self._messages = Queue()
        self._read_lock = Lock()
        self.client.on_message = self._on_message

    def _on_message(self, _client, _userdata, message):
        """
        The callback used to process each incoming message

        Args:
            _client (_type_): _description_
            _userdata (_type_): _description_
            message (_type_): _description_
        """
        self._messages.put((message.topic, message.payload))

    def connect(self):
        """
        Connects to the MQTT server and uses the set password and username to login.
        """

        self.client.username_pw_set(self.username_password,self.username_password)
        self.client.connect(self.mqtt_broker)
        self.client.loop_start()

    def publish(self, topic:str, payload:str, qos=0):
        """
        Publishes a payload to a given topic. Do note, my student ID mannually added to the topic.

        Args:
            topic (str): The MQTT topic
            payload (str): The data to be shared
            qos (int, optional): The quality of service. For the sake of this project, QOS of 0 is predominatly used. Defaults to 0.
        """
        self.client.publish(topic="{103218929}/"+f"{topic}", payload=str(payload), qos=qos)

    def subscribe(self, topic:str, qos:int = 0):
        """
        Subscribes to a given topic. 
        Use read or read_messages to get the latest data from the subscribed streams.

        Args:
            topic (str): Topic name (Again, I add my student ID to it)
            qos (int, optional): The QOS. Defaults to 0.

        Raises:
            RuntimeError: If the MQTT library could not find or subscribe to the target topic.
        """

        full_topic = "{103218929}/" + topic
        result, _ = self.client.subscribe(full_topic, qos=qos)
        if result != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"Could not subscribe to topic {full_topic!r}")

    def read_message(self, timeout=2) -> tuple[str,str]:
        """
        This function is used to interface with the callback queue which is generated when a topic is subscribed to.

        Args:
            timeout (_type_, optional): The timeout for getting a value from the shared Queue. Defaults to 2.

        Raises:
            ValueError: If the timeout is negative
            TimeoutError: If the timeout expires

        Returns:
            tuple[str,str]: Returns topic (str), payload(str) 
        """
        if timeout < 0:
            raise ValueError("timeout cannot be negative")

        try:
            topic, payload = self._messages.get(timeout=timeout)
        except Empty:
            raise TimeoutError("No MQTT message received before the timeout") from None
        return topic, payload.decode("utf-8")

    def disconnect(self):
        """
        Releases the MQTT resources
        """
        self.client.disconnect()
        self.client.loop_stop()
