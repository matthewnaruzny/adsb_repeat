import os
import time
import json

from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

import config


class ADSB_Controller:

    def __init__(self, aws_config):
        self.aws_config = aws_config
        self.mqtt_client = self.establish_aws_connection()

        # Start Monitoring
        self.monitor()

    def establish_aws_connection(self):
        private_path = os.path.abspath(self.aws_config['private_key'])
        cert_path = os.path.abspath(self.aws_config['cert'])
        root_path = os.path.abspath(self.aws_config['root_ca'])

        print("Configuring Client...")
        myMQTTClient = AWSIoTMQTTClient(self.aws_config['id'])
        myMQTTClient.configureEndpoint(self.aws_config['endpoint_addr'], self.aws_config['endpoint_port'])
        myMQTTClient.configureCredentials(root_path, private_path, cert_path)
        myMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
        myMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
        myMQTTClient.configureConnectDisconnectTimeout(15)  # 15 sec
        myMQTTClient.configureMQTTOperationTimeout(15)  # 15 sec

        print("Connecting to Endpoint...")
        try:
            myMQTTClient.connect()
            myMQTTClient.subscribe("adsb/" + self.aws_config['id'], 1, self.recv_message)
            print("adsb/" + self.aws_config['id'])
            print("Connected and Subscribed")
        except Exception:
            print("Failed to Connect")
            return

        return myMQTTClient

    def recv_message(msg):
        print("New Message: " + str(msg))

    def monitor(self):
        default_topic = "adsb/" + self.aws_config['id']
        os.chdir('/run/dump1090-mutability')

        while True:
            current_data = []
            with open("aircraft.json", "r") as f:
                a = json.load(f)
                t_aircraft = a['aircraft']
                print(t_aircraft)
                try:
                    self.mqtt_client.publish(default_topic + "/tracking/num", str(len(t_aircraft)), 1)
                    self.mqtt_client.publish(default_topic + "/tracking", str(t_aircraft), 1)
                    print("Published")
                except Exception:
                    print("Unable to Publish")

            time.sleep(5)
