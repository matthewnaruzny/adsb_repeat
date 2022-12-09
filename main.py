import argparse
import os
import subprocess
import time
import json

import config

if config.mode == "aws":
    from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
elif config.mode == "mqtt":
    import paho.mqtt.client as mqtt


class Watchlist:
    """
    Contains and manages a watchlist of aircraft and a database of aircraft information
    """

    def __init__(self, filename="watchlist.json", db_path='indexedDB_old/aircrafts.json', db_skip=False):
        self.filename = filename
        self.watchlist = []
        self.load_list()
        self.db_skip = db_skip

        if not db_skip:
            print("Loading Database...")
            self.db_path = db_path
            self.a_db = []
            self.db_load()
            print("Database Loaded")
        else:
            print("Skipping database loading.")
            self.a_db = []

    def db_loaded(self):
        return self.db_skip
    def db_load(self):
        """
        Loads aircraft database into memory. Required before retrieving records
        """
        with open(self.db_path, 'r') as f_db:
            self.a_db = json.load(f_db)

    def db_reload(self):
        self.a_db = []
        self.db_load()

    def db_network_update(self):
        subprocess.run(["sh", "./update_db.sh"])
        self.db_reload()


    def db_get(self, icao24):
        """
        Returns database record for the given icao24
        :param icao24: icao24 to search for in the database
        :return: Returns the database record for the icao24 if found. If not found, returns None.
        """
        icao24 = icao24.upper()
        if icao24 in self.a_db:
            return self.a_db[icao24]

        return None

    def load_list(self):
        """
        Loads watchlist from file into memory
        """
        if os.path.exists(self.filename):
            with open(self.filename, "r") as f:
                self.watchlist = json.load(f)
        else:
            with open(self.filename, "w") as f:
                f.write(json.dumps(self.watchlist))

    def add_object(self, obj):
        self.watchlist.append(obj)
        with open(self.filename, "w") as f:
            f.write(json.dumps(self.watchlist))

    def add(self, field, item, display_message):
        assert isinstance(field, str)
        assert isinstance(item, str)
        item = item.upper()
        x = {field: item, 'display_msg': display_message}
        self.add_object(x)

    def remove(self, field, item):
        if self.list_contains(field, item):
            for i in range(len(self.watchlist)):
                x = self.watchlist[i]
                if field in x:
                    if x[field] == item:
                        self.watchlist.pop(i)
                        return
        else:
            return False

    def find(self, icao24):  # Retrieves Watchlist Item
        assert isinstance(icao24, str)
        icao24 = icao24.upper()
        a_record = self.db_get(icao24)
        for i in self.watchlist:
            if 'icao24' in i:
                if i['icao24'] == icao24:
                    return i
            if 'mark' in i and a_record is not None:
                if i['mark'] == a_record['r']:
                    return i

        return False

    def get_display(self, icao24):
        return self.find(icao24)['display_msg']

    def list_contains(self, field, item):
        assert isinstance(field, str)
        assert isinstance(item, str)
        item = item.upper()
        for o in self.watchlist:
            if field in o:
                if o[field] == item:
                    return True
        return False

    def match_check(self, icao24):
        if self.list_contains('icao24', icao24):  # Check Provided icao24 (hex)
            return True

        a_record = self.db_get(icao24)
        if a_record is not None:
            if self.list_contains('mark', a_record['r']):  # Check Database Registration Mark
                return True

        return False


class MQTTController:

    def __init__(self, data_config, watchlist):
        assert isinstance(watchlist, Watchlist)
        self.data_config = data_config
        self.watchlist = watchlist

    def publish(self, topic, payload, qos):
        pass

    def on_message(self, topic, payload):
        print("ADSB NEW REMOTE MSG: " + payload)
        if payload.split()[0] == "watch_add":
            print("Adding to watchlist")
            icao24 = payload.split()[1].strip()
            id_msg = payload.split()[2].strip()
            self.watchlist.add('icao24', icao24, id_msg)
            self.publish(topic, "Adding to watchlist", 0)
        if payload.split()[0] == "watch_remove":
            print("Removing from watchlist")
            self.publish(topic, "Removing from watchlist", 0)
            icao24 = payload.split()[1].strip()
            self.watchlist.remove('icao24', icao24)
        if payload.split()[0] == "db_update":
            print("Updating Database")
            self.publish(topic, "Updating Database", 0)
            self.watchlist.db_network_update()
        if payload.split()[0] == "ping":
            self.publish(topic, "Pong", 0)


class AWSConnector(MQTTController):

    def __init__(self, data_config, watchlist):
        super().__init__(data_config, watchlist)
        self.aws_config = data_config.aws
        self.default_topic = "adsb/" + self.aws_config['id']
        self.aws_client = self.establish_connection()

    def aws_msg_recv(self, msg_client, userdata, message, **arg1):
        mqtt_topic = message.topic
        mqtt_msg = message.payload.decode('ASCII')
        self.on_message(mqtt_topic, mqtt_msg)

    def publish(self, topic, payload, qos):
        try:
            self.aws_client.publish(topic, payload, qos)
        except Exception:
            print("Publish Error")

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


class RemoteMQTTController(MQTTController):

    def __init__(self, data_config, watchlist):
        super().__init__(data_config, watchlist)
        self.mqtt_config = data_config.mqtt
        self.default_topic = "adsb/" + self.mqtt_config['client_name']
        self.client = self.establish_connection()
        self.client.loop_start()

    def establish_connection(self):
        m_client = mqtt.Client(client_id=self.mqtt_config['client_name'])
        m_client.username_pw_set(self.mqtt_config['username'], self.mqtt_config['password'])
        m_client.connect(self.mqtt_config['host'], self.mqtt_config['port'], 60)

        m_client.on_message = self.mqtt_msg_recv
        m_client.subscribe(self.default_topic, 0)
        return m_client

    def publish(self, topic, payload, qos):
        try:
            self.client.publish(topic, payload, qos)
        except Exception:
            print("General Publish Error")

    def mqtt_msg_recv(self, client, userdata, message):
        print("**MQTT MSG**")
        print(message.topic)
        print(message.payload.decode("utf-8"))
        print("****")
        self.on_message(message.topic, message.payload.decode("utf-8"))
        return


class LogFile:
    def __init__(self, path="log.txt"):
        self.path = path

    def write(self, content):
        with open(self.path, "a") as f:
            f.write(content)
            f.write('\n')

    def log(self, title, content):
        timestamp = time.time()
        log_line = "[" + str(timestamp) + '][' + str(title) + '] ' + str(content)
        self.write(log_line)

    def watchlist(self, a, a_record=None):
        if a_record is not None:
            self.log("ALERT", str(a['hex']) + ' ' + a_record['r'] + ' ' + a['ALERT_MSG'])
        else:
            self.log("ALERT", str(a['hex']) + ' ' + a['ALERT_MSG'])

    def error(self, error_msg):
        self.log("ERROR", error_msg)


class ADSBController:

    def __init__(self, config, db_skip=False):
        # Load Watchlist
        print("Loading Watchlist...")
        self.watchlist = Watchlist(db_skip=db_skip)
        print("Watchlist Loaded")

        self.logger = LogFile()

        # Remote Mode
        if config.mode == "aws":
            print("AWS Connection")
            self.c_enabled = True
            self.controller = AWSConnector(config, self.watchlist)
        elif config.mode == "mqtt":
            print("MQTT Connection")
            self.c_enabled = True
            self.controller = RemoteMQTTController(config, self.watchlist)
        else:
            print("MQTT Remote Disabled")
            self.c_enabled = False

        self.monitor()

    def monitor(self):

        old_alerts = []
        print("Starting Monitor")
        while True:
            if self.c_enabled:
                self.controller.publish(self.controller.default_topic + "/alive", str(time.time()), 1)

            with open("/run/dump1090-mutability/aircraft.json", "r") as f:
                a = json.load(f)
                t_aircraft = a['aircraft']
                if self.c_enabled:
                    try:
                        a_pub_json = json.dumps(t_aircraft)
                        self.controller.publish(self.controller.default_topic + "/tracking", str(a_pub_json), 1)
                    except Exception:
                        print("Current Aircraft Publish Error")
                        self.logger.error("Current Aircraft Publish Error")

                alerted = []
                with open('alerts.txt', 'w') as a_f:
                    a_f.write(str(time.time()) + '\n')
                # open('alerts.txt', 'w').close()

                # Check for Alerting Aircraft
                for aircraft in t_aircraft:
                    alert = False
                    aircraft['hex'] = aircraft['hex'].upper()

                    aircraft['ALERT_MSG'] = ""

                    # Watchlist Check
                    if self.watchlist.match_check(aircraft['hex']):
                        print("WATCHLIST ALERT: " + aircraft['hex'])
                        aircraft['ALERT_MSG'] = aircraft['ALERT_MSG'] + "**WATCHLIST ALERT: [" + str(
                            self.watchlist.get_display(aircraft['hex'])) + "]**"
                        alert = True

                    # Special Squawk Check
                    if 'squawk' in aircraft:
                        squawk = aircraft['squawk']
                        if squawk == '7700' or squawk == '7600' or squawk == '7500':
                            print("SQUAWK ALERT: " + aircraft['hex'] + " " + squawk)
                            aircraft['ALERT_MSG'] = aircraft['ALERT_MSG'] + "**SQUAWK ALERT: [" + str(
                                aircraft['squawk']) + "]**"
                            alert = True

                    # DB Mil Flag Check
                    try:
                        a_record = self.watchlist.db_get(aircraft['hex'])
                        if a_record is not None:
                            flags = a_record['f']
                            if flags[0] == '1':  # Military Flagged
                                aircraft['ALERT_MSG'] = aircraft['ALERT_MSG'] + "**MILITARY FLAG**"
                                alert = True
                    except KeyError:
                        pass

                    if alert:
                        with open('alerts.txt', 'a') as a_f:
                            # Add DB Record to Alert
                            try:
                                a_record = self.watchlist.db_get(aircraft['hex'])
                                if a_record is not None:
                                    aircraft['db-record'] = a_record
                            except KeyError:
                                pass
                            a_f.write(json.dumps(aircraft) + '\n')

                    if alert and aircraft['hex'] not in old_alerts:
                        try:
                            a_pub_json = json.dumps(aircraft)
                            if self.c_enabled:
                                self.controller.publish(self.controller.default_topic + "/tracking/alert",
                                                        str(a_pub_json), 1)
                            alerted.append(aircraft['hex'])

                            a_record = self.watchlist.get_display(aircraft['hex'])
                            if a_record is not None:
                                self.logger.watchlist(aircraft, a_record)
                            else:
                                self.logger.watchlist(aircraft)


                        except Exception:
                            print("Alert Publish Error")
                            self.logger.error("Alert Publish Error")
                    elif alert:
                        alerted.append(aircraft['hex'])

                old_alerts = alerted

            time.sleep(5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--fast_load', action='store_true') # Flag for fast load
    args = parser.parse_args()
    client = ADSBController(config, db_skip=args.fast_load)
