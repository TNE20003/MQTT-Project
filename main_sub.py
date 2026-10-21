import paho.mqtt.client as mqtt

from random import randint
from time import sleep

def on_connect(client, userdata, flags, rc, properties=None):
    print("Python connection result:", rc)

def on_message(client, userdata, message):
    print("Got message")

mqtt_broker = 'rule28.i4t.swin.edu.au'
client = mqtt.Client(client_id='Subscriber_103218929')
username_password = "{103218929}"
client.username_pw_set(username_password,username_password)
client.connect(mqtt_broker)


client.loop_start()
client.subscribe('103218929/TEST_publish', qos=0)
client.on_message = on_message
sleep(30)
client.loop_stop()