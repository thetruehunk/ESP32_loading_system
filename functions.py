import NFC_PN532 as nfc
from machine import Pin, SPI
import machine
import utime as time
import ubinascii
import network
import ujson as json
import uasyncio as asyncio
import urequests as requests
import errno

ip_addr = ''

#################################
def load_config(config_file):
    try:
        with open(config_file) as f:
            config = json.load(f)
        return config    
    except:
        # OSError: [Errno 2] ENOENT
        print('No such config file:', config_file)
        time.sleep(5)
        machine.reset()


def save_config(config):
    pass


def load_data(config):
    if config["mode"] == "server":
        data_file = "data.json"
    with open(data_file) as d:
        data_f = json.load(d)


def save_data():
    with open(data_file, "w") as w:
        json.dump(data_f, w)

##### hardware functions #####
def wifi_init():
    config = load_config('config.json')
    global ip_addr
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
            print(2)
            wifi_if.disconnect()
            wifi_if.active(False)
            wifi_if = network.WLAN(network.AP_IF)
            wifi_if.active(True)
            wifi_if.config(essid=(config["AP-ESSID"]), password=(config["AP-PASSWORD"]))
            wifi_if.ifconfig(('192.168.100.1', '255.255.255.0', '192.168.100.1', '8.8.8.8'))
        print('network config:', wifi_if.ifconfig())
    ip_addr = wifi_if.ifconfig()[0] 

def init_card_reader():
    # PN532 module connect and initialize
    try:
        spi_dev = SPI(baudrate=1000000, sck=Pin(5), mosi=Pin(23), miso=Pin(19))
        cs = Pin(22, Pin.OUT)
        cs.on()
        pn532 = nfc.PN532(spi_dev, cs)
        ic, ver, rev, support = pn532.get_firmware_version()
        print("Found PN532 with firmware version: {0}.{1}".format(ver, rev))
        pn532.SAM_configuration()
        return pn532
    except RuntimeError:
        machine.reset()


def read_card(dev, tmot, relay, config):
    """Accepts a device and a timeout in millisecs """
    print("Reading...")
    uid = dev.read_passive_target(timeout=tmot)
    if uid is None:
        print("CARD NOT FOUND")
    else:
        # если мы клиент - запрашиваем данные с сервера
        global data_f
        if config["mode"] == "client":
            req = requests.get("http://" + config["server-ip"] + "/data.json")
            data_f = json.loads(req.text)
        numbers = [i for i in uid]
        string_ID = "{}-{}-{}-{}".format(*numbers)
        print("Card number is {}".format(string_ID))
        row = get_row_by_key(data_f, string_ID)
        if row:
            if string_ID in row and row[2] > 0:
                # if выдано 2 порции day limit
                print("Loading....")
                relay.off()
                time.sleep(2.5)  # задержка реле (время налива)
                relay.on()
                data_f[row[0]] = {
                    row[1]: (row[2] - 1),
                    "day limit": row[3],
                    "realese count": (row[4] + 1),
                }  # списываем одну процедуру
                # сейчас сохраняем данные после каждого списания
                if config["mode"] == "server":
                    save_data()
                else:
                    try:
                        requests.get(
                            "http://"
                            + config["server-ip"]
                            + "/set_limit?day_limit="
                            + str(row[3])
                            + "&"
                            + row[0]
                            + "_"
                            + row[1]
                            + "="
                            + str(row[2] - 1)
                        )
                    except NotImplementedError:  # нужен для обхода не реализованных route в библиотеке requests
                        pass
                time.sleep(3)
            else:
                pass


def read_card_loop(relay, config):
    pn532 = init_card_reader()
    while True:
        try:
            read_card(pn532, 500, relay, config)
            await asyncio.sleep(1)
        except RuntimeError:
            print("RuntimeError")
        except OSError:
            print("Server not found")


########################
def get_row_by_key(data_json, card_number):
    for keys, values in data_json.items():
        if card_number in values.keys():
            return (
                keys,
                card_number,
                values[card_number],
                values["day limit"],
                values["realese count"],
            )


##### WEB handlers #####
def set_limit_handler(qs):
    result1 = qs.replace("_", "=")
    result2 = result1.replace("&", "=")
    result3 = result2.split("=")
    day_limit_value = result3[2]
    number = result3[3]
    card = result3[4]
    value = result3[5]
    data_f[number][card] = int(value)
    data_f[number]["day limit"] = int(day_limit_value)
    save_data()
