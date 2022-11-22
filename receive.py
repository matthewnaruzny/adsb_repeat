import time
import paramiko
import json
import ctypes
import winsound

from receive_config import r_config

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

old_alert = []

print("**ADSB Remote Receiver**")

while True:
    try:
        if 'pk_path' in r_config:
            pkey = paramiko.RSAKey.from_private_key_file(r_config['pk_path'])
            client.connect(hostname=r_config['hostname'], username=r_config['username'], password=r_config['password'],
                           port=r_config['port'], pkey=pkey, look_for_keys=False)
        else:
            client.connect(hostname=r_config['hostname'], username=r_config['username'], password=r_config['password'],
                           port=r_config['port'], look_for_keys=False)
        print("Connected to ADSB Receiver")
    except Exception:
        print("Unable to Connect")
        time.sleep(5)
        continue

    while True:
        try:
            stdin, stdout, stderr = client.exec_command('cat /home/pi/adsb_upload/adsb_repeat/alerts.txt')
            lines = stdout.readlines()
            try:
                alerted = []
                aircrafts = []
                for line in lines:
                    aircraft = json.loads(line)
                    alerted.append(aircraft['hex'])
                    aircrafts.append(aircraft)

                if alerted != old_alert:
                    old_alert = alerted
                    if len(alerted) > 0:
                        a_line = "**ADSB Alert**\n"
                        for aircraft in aircrafts:

                            if 'flight' in aircraft:
                                t_line = aircraft['flight'] + '  '
                            else:
                                t_line = ''

                            if 'squawk' in aircraft:
                                t_line = t_line + aircraft['hex'] + " " + str(aircraft['squawk']) + " :" + aircraft['ALERT_MSG'] + "\n"
                            else:
                                t_line = t_line + aircraft['hex'] + " :" + aircraft['ALERT_MSG'] + "\n"

                            a_line = a_line + t_line

                        winsound.Beep(440, 750)
                        ctypes.windll.user32.MessageBoxW(0, a_line, "ADSB ALERT", 0x1000)

            except json.decoder.JSONDecodeError:
                print("Error Reading Data... File could be misplaced or empty")

            time.sleep(5)
        except ConnectionResetError:
            print("Execution Error")
            break
