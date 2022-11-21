import time
import paramiko
import json
import ctypes

from receive_config import r_config


client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())


while True:
    try:
        if 'pk_path' in r_config:
            pkey = paramiko.RSAKey.from_private_key_file(r_config['pk_path'])
            client.connect(hostname=r_config['hostname'], username=r_config['username'], password=r_config['password'],
                           port=r_config['port'], pkey=pkey, look_for_keys=False)
        else:
            client.connect(hostname=r_config['hostname'], username=r_config['username'], password=r_config['password'],
                           port=r_config['port'], look_for_keys=False)

    except Exception:
        print("Unable to Connect")
        continue

    while True:
        try:
            stdin, stdout, stderr = client.exec_command('cat /home/pi/adsb_upload/adsb_repeat/alerts.txt')
            line = stdout.readline()
            print(line)
            try:
                alerts = json.loads(line)
                # Create Popup
                if len(alerts) > 0:
                    a_line = "**ADSB Alert**\n"
                    for a in alerts:
                        a_line = a_line + str(a) + "\n"

                    ctypes.windll.user32.MessageBoxW(0, a_line, "ADSB ALERT", 1)
            except json.decoder.JSONDecodeError:
                print("Error Reading Data... File could be misplaced or empty")


            time.sleep(5)
        except ConnectionResetError:
            print("Execution Error")
            break
