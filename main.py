import paho.mqtt.client as mqtt

from random import randint
from time import sleep

def on_connect(client, userdata, flags, rc, properties=None):
    print("Python connection result:", rc)

mqtt_broker = 'rule28.i4t.swin.edu.au'
client = mqtt.Client(client_id="ABCDC123", clean_session=True)
username_password = "{103218929}"
client.username_pw_set(username_password,username_password)
client.connect(mqtt_broker)

client.loop_start()
print("I am alive")
while True:
    try:
        _payload = randint(0,10)
        resp = client.publish(topic='103218929/TEST_publish', payload=str(_payload), qos=0)
        # resp.wait_for_publish(2)
        # if resp.is_published():
        #     print(f"Published successfully {_payload}")
        # sleep(1)

    except KeyboardInterrupt:
        client.disconnect()
        client.loop_stop()
        break

    except RuntimeError:
        client.disconnect()
        client.loop_stop()
        break
# client.loop_stop()


