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
        print("Unable to Connect. Will retry in 20 seconds.")
        time.sleep(20)
        continue

    while True:
        try:
            stdin, stdout, stderr = client.exec_command('cat /home/pi/adsb_upload/adsb_repeat/alerts.txt')
            lines = stdout.readlines()
            try:
                alerted = []
                aircrafts = []
                if len(lines) == 0:
                    print("File Error. Waiting 20 seconds then will check again.")
                    time.sleep(20)
                    continue
                update_time = float(lines[0])
                lines.pop(0)
                if abs(update_time-time.time()) > 10:
                    print("Out of Date by: " + str(round(abs(update_time-time.time()))) + "seconds. Waiting 20 "
                                                                                          "seconds then will check "
                                                                                          "again.")
                    time.sleep(20)
                    continue

                for line in lines:
                    aircraft = json.loads(line)
                    alerted.append(aircraft['hex'])
                    aircrafts.append(aircraft)

                if alerted != old_alert:
                    old_alert = alerted
                    if len(alerted) > 0:
                        a_line = "**ADSB Alert**\n"
                        for aircraft in aircrafts:

                            if 'db-record' in aircraft:
                                t_line = aircraft['db-record']['r'] + '  '
                            else:
                                t_line = ''

                            if 'squawk' in aircraft:
                                t_line = t_line + "icao24: " + aircraft['hex'] + " Squawk: " + str(aircraft['squawk']) + " :" + aircraft['ALERT_MSG'] + "\n"
                            else:
                                t_line = t_line + "icao24: " + aircraft['hex'] + " :" + aircraft['ALERT_MSG'] + "\n"

                            a_line = a_line + t_line

                        winsound.Beep(440, 750)
                        print(a_line)
                        ctypes.windll.user32.MessageBoxW(0, a_line, "ADSB ALERT", 0x1000)

            except json.decoder.JSONDecodeError:
                print("Error Reading Data... File could be misplaced or empty")

            time.sleep(5)
        except ConnectionResetError: # Network Disconnect
            print("Connection Error. Connection Closed")
            break
        except EOFError:
            print("Connection Error")
            break
        except paramiko.ssh_exception.SSHException:
            print("Session Closed. Error")
            break
