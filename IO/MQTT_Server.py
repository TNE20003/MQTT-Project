import paho.mqtt.client as mqtt
from queue import Empty, Queue
from threading import Lock
from time import monotonic


class MQTTServer:
    def __init__(self, client_id):
        self.mqtt_broker = 'rule28.i4t.swin.edu.au'
        self.client = mqtt.Client(client_id=client_id, clean_session=True)
        self.username_password = "{103218929}"
        self._messages = Queue()
        self._read_lock = Lock()
        self.client.on_message = self._on_message

    def _on_message(self, _client, _userdata, message):
        self._messages.put((message.topic, message.payload))
    
    def connect(self):
        self.client.username_pw_set(self.username_password,self.username_password)
        self.client.connect(self.mqtt_broker)
        self.client.loop_start()

    def publish(self, topic, payload, qos=0):
        self.client.publish(topic="{103218929}/"+f"{topic}", payload=str(payload), qos=qos)

    def subscribe(self, topic, qos=0):
        full_topic = "{103218929}/" + topic
        result, _ = self.client.subscribe(full_topic, qos=qos)
        if result != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"Could not subscribe to topic {full_topic!r}")

    def read_message(self, timeout=None):
        if timeout is not None and timeout < 0:
            raise ValueError("timeout cannot be negative")

        try:
            topic, payload = self._messages.get(timeout=timeout)
        except Empty:
            raise TimeoutError("No MQTT message received before the timeout") from None
        return topic, payload.decode("utf-8")

    def read(self, topic, timeout=5.0):
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")

        full_topic = "{103218929}/" + topic
        with self._read_lock:
            while not self._messages.empty():
                self._messages.get_nowait()

            result, _ = self.client.subscribe(full_topic)
            if result != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError(f"Could not subscribe to topic {full_topic!r}")

            deadline = monotonic() + timeout
            try:
                while True:
                    remaining = deadline - monotonic()
                    if remaining <= 0:
                        raise TimeoutError(f"No message received on topic {full_topic!r} within {timeout} seconds")

                    try:
                        message_topic, payload = self._messages.get(timeout=remaining)
                    except Empty:
                        raise TimeoutError(
                            f"No message received on topic {full_topic!r} within {timeout} seconds"
                        ) from None

                    if message_topic == full_topic:
                        return payload.decode("utf-8")
            finally:
                self.client.unsubscribe(full_topic)

    def disconnect(self):
        self.client.disconnect()
        self.client.loop_stop()
