import ujson as json
import network
import time


def do_connect():
        config_file = 'config.json'
        with open(config_file) as f:
                config = json.load(f)
        global ip_address
        wifi_if = network.WLAN(network.STA_IF)
        if not wifi_if.isconnected():
                print('connecting to network...')
        wifi_if.active(True)
        wifi_if.connect(config["ESSID"], config["PASSWORD"])

        #  Try connect to Access Point
        a = 0

        while not wifi_if.isconnected() and a != 5:
                print('.', end='')
                time.sleep(5)
                a += 1
                pass

        
        # If module cannot connect to WiFi - he's creates personal AP
        if not wifi_if.isconnected():
                wifi_if.disconnect()
                wifi_if.active(False)
                wifi_if = network.WLAN(network.AP_IF)
                wifi_if.active(True)
                wifi_if.config(essid=(config["AP-ESSID"]), password=(config["AP-PASSWORD"]))
                wifi_if.ifconfig(('192.168.100.1', '255.255.255.0', '192.168.100.1', '8.8.8.8'))

        
        print('network config:', wifi_if.ifconfig())
        ip_address = wifi_if.ifconfig()[0]
