import os
import time
import json

from tabulate import tabulate

# from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

# myMQTTClient = AWSIoTMQTTClient("adsb-repeater-0001")
# myMQTTClient.configureEndpoint("YOUR.ENDPOINT", 8883)
# myMQTTClient.configureCredentials("certs/root-CA.crt", "certs/adsb_remote_0001.private.key",
#                                  "certs/adsb_remote_0001.cert.pem")
# myMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
# myMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
# myMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
# myMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec

os.chdir('/run/dump1090-mutability')


def recv_message(msg):
    print(msg)


# myMQTTClient.connect()
# myMQTTClient.subscribe("adsb/remote/0001", 1, recv_message)

while True:
    os.system("clear")
    current_data = []
    print("---------------Flight Data---------------")
    with open("aircraft.json", "r") as f:
        a = json.load(f)
        t_aircraft = a['aircraft']
        for i in t_aircraft:
            current_data.append([i['hex'], i['flight'], i['squawk'], i['altitude'], i['speed'], i['lat'], i['lon']])

        print(tabulate(current_data, headers=["icao24", "Flight #", "Squawk", "Alt", "Speed", "lat", "long"]))

    print("-----------------------------------------")
    time.sleep(1)
