import os
import time
import json

from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

import config


class ADSBController:

    def __init__(self, aws_config):
        self.aws_config = aws_config
        self.mqtt_client = self.establish_aws_connection()

        self.watchlist = self.load_watchlist()

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
        # myMQTTClient.onMessage = self.recv_message

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

    def recv_message(self, msg_client, userdata, message, **arg1):
        mqtt_topic = message.topic
        mqtt_msg = message.payload.decode('ASCII')
        if mqtt_msg.split()[0] == "watch_add":
            icao24 = mqtt_msg.split()[1].strip()
            self.watchlist_add(icao24)
        if mqtt_msg.split()[0] == "watch_remove":
            icao24 = mqtt_msg.split()[1].strip()
            self.watchlist_remove(icao24)

    def load_watchlist(self, filename="watchlist.txt"):
        new_watchlist = []
        print("** Loading Watchlist **")
        if os.path.exists(filename):
            with open(filename, "r") as f:
                for l in f.readlines():
                    print(l)
                    new_watchlist.append(l.strip())
        print("** Done **")
        return new_watchlist

    def watchlist_add(self, icao24, filename="watchlist.txt"):
        self.watchlist.append(icao24)
        print("Adding " + str(icao24) + " to watchlist.")
        with open(filename, "a") as watchlist_file:
            watchlist_file.write(str(icao24) + '\n')

    def watchlist_remove(self, icao24, filename="watchlist.txt"):
        self.watchlist.remove(icao24)
        print("Removing " + str(icao24) + " from watchlist.")
        with open(filename, "r") as watchlist_file:
            watched_lines = watchlist_file.readlines()
        with open(filename, "w") as watchlist_file:
            for line in watched_lines:
                if line.strip("\n") != icao24:
                    watchlist_file.write(line)

    def monitor(self):
        default_topic = "adsb/" + self.aws_config['id']

        old_alerts = []

        while True:
            with open("/run/dump1090-mutability/aircraft.json", "r") as f:
                a = json.load(f)
                t_aircraft = a['aircraft']
                try:
                    a_pub_json = json.dumps(t_aircraft)
                    self.mqtt_client.publish(default_topic + "/tracking", str(a_pub_json), 1)
                except Exception:
                    print("General Publish Error")

                alerted = []
                for aircraft in t_aircraft:
                    alert = False

                    if aircraft['hex'] in self.watchlist:
                        print("WATCHLIST ALERT: " + aircraft['hex'])
                        aircraft['ALERT_W'] = "WATCHLIST ALERT"
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
                            self.mqtt_client.publish(default_topic + "/tracking/alert", str(a_pub_json), 1)
                            alerted.append(aircraft['hex'])

                        except Exception:
                            print("Alert Publish Error")
                    elif alert:
                        alerted.append(aircraft['hex'])

                old_alerts = alerted

            time.sleep(5)


client = ADSBController(config.aws)
