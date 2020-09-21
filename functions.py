import errno

import machine
import network
import NFC_PN532 as nfc
import uasyncio as asyncio
import ubinascii
import ujson as json
import ulogging as logging
import urequests as requests
import utime as time
from machine import SPI, Pin

ip_addr = ""

def load_config(config_file):
    try:
        with open(config_file) as f:
            config = json.load(f)
        return config
    except:
        # OSError: [Errno 2] ENOENT
        print("No such config file:", config_file)
        time.sleep(5)
        machine.reset()


def save_config(config, config_file):
    try:
        with open(config_file, "w") as f:
            json.dump(config, f)
    except:
        logging.info("No such config file:", config_file) 


def load_data(data_file):
    try:
        with open(data_file) as d:
            data = json.load(d)
        return data
    except:
        logging.info("No such data file:", data_file)


def save_data(data, data_file):
    with open(data_file, "w") as d:
        json.dump(data, d)


def set_limit_handler(qs):
    data_f = load_data("data.json")
    result1 = qs.replace("_", "=")
    result2 = result1.replace("&", "=")
    result3 = result2.split("=")
    day_limit_value = result3[2]
    number = result3[3]
    card = result3[4]
    value = result3[5]
    data_f[number][card] = int(value)
    data_f[number]["day limit"] = int(day_limit_value)
    save_data(data_f, "data.json")


def set_config_handler(qs):
    config = load_config("config.json")
    param = qs.split('&')
    for item in param:
        key, value = item.split('=')
        config[key] = value
    if not 'SERVER=True' in qs:
        config['SERVER'] = "False"
    save_config(config, 'config.json')


def wifi_init():
    config = load_config("config.json")
    global ip_addr
    try:
        wifi_if = network.WLAN(network.STA_IF)
        if not wifi_if.isconnected():
            print("connecting to network...")
        wifi_if.active(True)
        wifi_if.connect(config["ESSID"], config["PASSWORD"])
        #  Try connect to Access Point
        a = 0
        while not wifi_if.isconnected() and a != 5:
            print(".", end="")
            time.sleep(5)
            a += 1
            # If module cannot connect to WiFi - he's creates personal AP
        if not wifi_if.isconnected():
            wifi_if.disconnect()
            wifi_if.active(False)
            wifi_if = network.WLAN(network.AP_IF)
            wifi_if.active(True)
            wifi_if.config(essid=(config["AP-ESSID"]), authmode=network.AUTH_WPA_WPA2_PSK, password=(config["AP-PASSWORD"]), channel=int(config["CHANNEL"]))
            wifi_if.ifconfig(
                ("10.27.10.1", "255.255.255.0", "10.27.10.1", "10.27.10.1")
            )
        print("network config:", wifi_if.ifconfig())
        ip_addr = wifi_if.ifconfig()[0]
    except RuntimeError:
        logging.info("Cannot init wifi")
        time.sleep(5)
        machine.reset()

def check_wifi_status():
    pass
    # TODO:
    # WLAN.status([param])
    # Return the current status of the wireless connection.
    # When called with no argument the return value describes the network link status.
    # The possible statuses are defined as constants:
    # STAT_IDLE – no connection and no activity,
    # STAT_CONNECTING – connecting in progress,
    # STAT_WRONG_PASSWORD – failed due to incorrect password,
    # STAT_NO_AP_FOUND – failed because no access point replied,
    # STAT_CONNECT_FAIL – failed due to other problems,
    # STAT_GOT_IP – connection successful.

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
        logging.info("Card reader not initialized")
        time.sleep(5)
        machine.reset()


def check_card_reader():
    pass


def read_card(dev, tmot, relay, config):
    """Accepts a device and a timeout in millisecs """
    print("Reading...")
    uid = dev.read_passive_target(timeout=tmot)
    if uid is None:
        print("CARD NOT FOUND")
    else:
        # если мы клиент - запрашиваем данные с сервера
        global data_f
        if config["SERVER"] == "False":
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
                # if config["SERVER"] == "True":
                #     save_data()
                # else:
                #     try:
                #         requests.get(
                #             "http://"
                #             + config["server-ip"]
                #             + "/set_limit?day_limit="
                #             + str(row[3])
                #             + "&"
                #             + row[0]
                #             + "_"
                #             + row[1]
                #             + "="
                #             + str(row[2] - 1)
                #         )
                #     except NotImplementedError:  # нужен для обхода не реализованных route в библиотеке requests
                #         pass
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


def require_auth(func):
    config = load_config('config.json')
    def auth(req, resp):
        auth = req.headers.get(b"Authorization")
        if not auth:
            yield from resp.awrite(
                "HTTP/1.0 401 NA\r\n"
                'WWW-Authenticate: Basic realm="Picoweb Realm"\r\n'
                "\r\n"
            )
            return

        auth = auth.split(None, 1)[1]
        auth = ubinascii.a2b_base64(auth).decode()
        req.username, req.passwd = auth.split(":", 1)
        if not (
            (req.username == config["WEB-LOGIN"])
            and (req.passwd == config["WEB-PASSWORD"])
        ):
            yield from resp.awrite(
                "HTTP/1.0 401 NA\r\n"
                'WWW-Authenticate: Basic realm="Picoweb Realm"\r\n'
                "\r\n"
            )
            return

        yield from func(req, resp)

    return auth
