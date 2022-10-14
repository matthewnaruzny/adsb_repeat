import os
import time
import json

from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

import config
aws_config = config.aws

private_path = os.path.abspath(aws_config['private_key'])
cert_path = os.path.abspath(aws_config['cert'])
root_path = os.path.abspath(aws_config['root_ca'])
print(private_path)
print(cert_path)
print(root_path)

print(config.aws)

print("Setting Up...")
myMQTTClient = AWSIoTMQTTClient(aws_config['id'])
myMQTTClient.configureEndpoint(aws_config['endpoint_addr'], aws_config['endpoint_port'])
myMQTTClient.configureCredentials(root_path, private_path, cert_path)
myMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
myMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
myMQTTClient.configureConnectDisconnectTimeout(15)  # 15 sec
myMQTTClient.configureMQTTOperationTimeout(15)  # 15 sec


def recv_message(msg):
    print("New Message: " + str(msg))


print("Connecting...")
myMQTTClient.connect()
myMQTTClient.subscribe("adsb/" + aws_config['id'], 1, recv_message)
print("adsb/" + aws_config['id'])
print("Connected and Subscribed")

default_topic = "adsb/" + aws_config['id']

os.chdir('/run/dump1090-mutability')

while True:
    current_data = []
    with open("aircraft.json", "r") as f:
        a = json.load(f)
        t_aircraft = a['aircraft']
        print(t_aircraft)
        try:
            myMQTTClient.publish(default_topic + "/tracking/num", str(len(t_aircraft)), 1)
            myMQTTClient.publish(default_topic + "/tracking", str(t_aircraft), 1)
            print("Published")
        except Exception:
            print("Unable to Publish")

    time.sleep(5)
