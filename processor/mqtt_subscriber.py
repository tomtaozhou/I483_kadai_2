import paho.mqtt.client as mqtt

STUDENT = "s2510085"
BROKER  = "150.65.230.59"
PORT    = 1883
TOPIC   = "i483/sensors/{}/#".format(STUDENT)


def on_connect(client, userdata, flags, rc):
    print("Connected, rc=", rc)
    client.subscribe(TOPIC)
    print("Subscribed:", TOPIC)


def on_message(client, userdata, msg):
    print("{:60s} -> {}".format(msg.topic, msg.payload.decode()))


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)
client.loop_forever()