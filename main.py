import os
import time
import json

import config

aws_config = config.aws

from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient


private_path = os.path.abspath(aws_config['private_key'])
cert_path = os.path.abspath(aws_config['cert'])
root_path = os.path.abspath(aws_config['root_ca'])

myMQTTClient = AWSIoTMQTTClient(aws_config['id'])
myMQTTClient.configureEndpoint(aws_config['endpoint_addr'], aws_config['endpoint_port'])
myMQTTClient.configureCredentials(root_path, private_path, cert_path)
myMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
myMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
myMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
myMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec

os.chdir('/run/dump1090-mutability')


def recv_message(msg):
    print(msg)


myMQTTClient.connect()
myMQTTClient.subscribe("adsb/remote/" + aws_config['id'], 1, recv_message)

repeat_num = aws_config['id'].split('_')[2]
default_topic = "adsb/remote/" + repeat_num


while True:
    os.system("clear")
    current_data = []
    with open("aircraft.json", "r") as f:
        a = json.load(f)
        t_aircraft = a['aircraft']
        myMQTTClient.publish(default_topic + "/tracking/num", len(t_aircraft), 1)
        myMQTTClient.publish(default_topic + "/tracking", t_aircraft, 1)

    time.sleep(1)
