import os
import time
import json

from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

import config


class Watchlist:

    def __init__(self, filename="watchlist.txt"):
        self.filename = filename
        self.watchlist = {}
        self.loadList()

    def loadList(self):
        if os.path.exists(self.filename):
            with open(self.filename, "r") as f:
                for line in f.readlines():
                    ls = line.strip().lower().split()
                    self.watchlist[ls[0]] = ls[1]

    def add(self, icao24, display_message):
        icao24 = icao24.lower()
        if icao24 in self.watchlist.keys():
            return False

        self.watchlist[icao24] = display_message
        print("Adding " + str(icao24) + " to watchlist.")
        with open(self.filename, "a") as watchlist_file:
            watchlist_file.write(str(icao24) + ' ' + str(display_message) + '\n')
        return True

    def remove(self, icao24):
        icao24 = icao24.lower()
        if icao24 not in self.watchlist.keys():
            return False

        self.watchlist.pop(icao24)
        print("Removing " + str(icao24) + " from watchlist.")
        with open(self.filename, "r") as watchlist_file:
            watched_lines = watchlist_file.readlines()
        with open(self.filename, "w") as watchlist_file:
            for line in watched_lines:
                if line.strip("\n").split()[0] != icao24:
                    watchlist_file.write(line)
        return True

    def contains(self, icao24):
        return icao24 in self.watchlist.keys()

    def getDisplay(self, icao24):
        return self.watchlist[icao24]


class MQTTController:

    def __init__(self, data_config, watchlist):
        self.data_config = data_config
        self.watchlist = watchlist

    def on_message(self, payload):
        if payload.split()[0] == "watch_add":
            icao24 = payload.split()[1].strip().lower()
            id_msg = payload.split()[2].strip()
            self.watchlist.add(icao24, id_msg)
        if payload.split()[0] == "watch_remove":
            icao24 = payload.split()[1].strip()
            self.watchlist.remove(icao24)


class AWSConnector(MQTTController):

    def __init__(self, data_config, watchlist):
        super().__init__(data_config, watchlist)
        self.aws_config = data_config.aws
        self.default_topic = "adsb/" + self.aws_config['id']
        self.aws_client = self.establish_connection()

    def aws_msg_recv(self, msg_client, userdata, message, **arg1):
        mqtt_topic = message.topic
        mqtt_msg = message.payload.decode('ASCII')
        self.on_message(mqtt_msg)

    def publish(self, topic, payload, qos):
        self.aws_client.publish(topic, payload, qos)

    def establish_connection(self):
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
            myMQTTClient.subscribe("adsb/" + self.aws_config['id'], 1, self.aws_msg_recv)
            print("adsb/" + self.aws_config['id'])
            print("Connected and Subscribed")
        except Exception:
            print("Failed to Connect")
            return

        return myMQTTClient


class ADSBController:

    def __init__(self, config):
        # Load Watchlist
        self.watchlist = Watchlist()

        # Remote Mode
        if config.mode == "aws":
            self.controller = AWSConnector(config, self.watchlist)

    def monitor(self):

        old_alerts = []

        while True:
            with open("/run/dump1090-mutability/aircraft.json", "r") as f:
                a = json.load(f)
                t_aircraft = a['aircraft']
                try:
                    a_pub_json = json.dumps(t_aircraft)
                    self.controller.publish(self.controller.default_topic + "/tracking", str(a_pub_json), 1)
                except Exception:
                    print("General Publish Error")

                alerted = []
                for aircraft in t_aircraft:
                    alert = False

                    if self.watchlist.contains(aircraft['hex']):
                        print("WATCHLIST ALERT: " + aircraft['hex'])
                        aircraft['ALERT_W'] = "WATCHLIST ALERT"
                        aircraft['ALERT_W_DISPLAY'] = self.watchlist.getDisplay(aircraft['hex'])
                        alert = True
                    if 'squawk' in aircraft:
                        squawk = aircraft['squawk']
                        if squawk == '7700' or squawk == '7600' or squawk == '7500':
                            print("SQUAWK ALERT: " + aircraft['hex'] + " " + squawk)
                            aircraft['ALERT_S'] = "SQUAWK ALERT"
                            alert = True

                    if alert and aircraft['hex'] not in old_alerts:
                        try:
                            a_pub_json = json.dumps(aircraft)
                            self.controller.publish(self.controller.default_topic + "/tracking/alert",
                                                    str(a_pub_json), 1)
                            alerted.append(aircraft['hex'])

                        except Exception:
                            print("Alert Publish Error")
                    elif alert:
                        alerted.append(aircraft['hex'])

                old_alerts = alerted

            time.sleep(5)


client = ADSBController(config.aws)
