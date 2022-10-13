import os
import time
import json

aircraft = {}

os.chdir('/run/dump1090-mutability')

while True:
    with open("aircraft.json", "r") as f:
        a = json.load(f)
        print(a)
    time.sleep(1)
