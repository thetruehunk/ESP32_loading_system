import picoweb
import ujson as json
import uasyncio as asyncio
import urequests as requests
import ubinascii
import utime as time
from machine import Pin, SPI
import machine
import NFC_PN532 as nfc
from functions import load_config, ip_addr


relay = Pin(18, Pin.OUT)


def load_data(data_file):
    config = load_config('config.json')
    if config["mode"] == "server":
        data_file = "data.json"
    with open(data_file) as d:
        data_f = json.load(d)
    return data_f


def save_data(data_file):
    with open(data_file, "w") as w:
        json.dump(data_file, w)


def set_limit_handler(qs):
    data_f = load_data('data.json')
    result1 = qs.replace("_", "=")
    result2 = result1.replace("&", "=")
    result3 = result2.split("=")
    day_limit_value = result3[2]
    number = result3[3]
    card = result3[4]
    value = result3[5]
    data_f[number][card] = int(value)
    data_f[number]["day limit"] = int(day_limit_value)
    save_data('data.json')


def require_auth(func):
    def auth(req, resp):
        config = load_config('config.json')
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
            (req.username == config["web-login"])
            and (req.passwd == config["web-passwd"])
        ):
            yield from resp.awrite(
                "HTTP/1.0 401 NA\r\n"
                'WWW-Authenticate: Basic realm="Picoweb Realm"\r\n'
                "\r\n"
            )
            return

        yield from func(req, resp)

    return auth


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


def read_card(dev, tmot):
    """Accepts a device and a timeout in millisecs """
    config = load_config('config.json')
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
                    save_data('data.json')
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


def read_card_loop():
    pn532 = init_card_reader()
    while True:
        try:
            read_card(pn532, 500)
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


app = picoweb.WebApp(__name__)

@app.route("/")
@require_auth
def send_index(req, resp):
    yield from app.sendfile(resp, "/www/index.html")


@app.route("/data.json")
def send_data(req, resp):
    yield from app.sendfile(resp, "data.json")


@app.route("/set_limit")
def set_limit(req, resp):
    if req.method == "GET":
        set_limit_handler(req.qs)
        headers = {"Location": "/"}
        yield from picoweb.start_response(resp, status="303", headers=headers)

    else:  # GET, apparently
        pass


loop = asyncio.get_event_loop()
loop.create_task(read_card_loop())

app.run(debug=1, host=ip_addr, port=80)
