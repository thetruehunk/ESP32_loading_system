import machine
import NFC_PN532 as nfc
import picoweb
import uasyncio as asyncio
import ubinascii
import ujson as json
import ulogging as logging
import urequests as requests
import utime as time
from functions import (
    ip_addr,
    load_config,
    init_card_reader,
    get_row_by_key,
    save_data,
    save_config,
    load_data,
    set_config_handler,
    set_limit_handler,
    require_auth,
)
import usyslog
from machine import SPI, Pin


logging.basicConfig(level=logging.INFO)

relay = Pin(18, Pin.OUT)

pn532 = init_card_reader()

# config = load_config('config.json')

def read_card(dev, tmot):
    """Accepts a device and a timeout in millisecs """
    config = load_config("config.json")
    # s = usyslog.UDPClient(ip=config["SYSLOG_SERVER_IP"])
    # s.info('TEST')
    print("Reading...")
    uid = dev.read_passive_target(timeout=tmot)
    if uid is None:
        logging.info("CARD NOT FOUND")
    else:
        # если мы клиент - запрашиваем данные с сервера
        global data_f
        if config["SERVER"] == "False":
            req = requests.get("http://" + config["SERVER-IP"] + "/data.json")
            data_f = json.loads(req.text)
        else:
            data_f = load_data('data.json')
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
                #     save_data("data.json")
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
        else:
            logging.info('Card not in list or limit is ower')


def read_card_loop(reader):
    while True:
        try:
            read_card(reader, 500)
            await asyncio.sleep(1)
        except RuntimeError:
            logging.info("Cannot get data from reader")
            time.sleep(5)
            machine.reset()
        except OSError as er:
            logging.info("OSError {}".format(er))


app = picoweb.WebApp(__name__)


@app.route("/")
@require_auth
def send_index(req, resp):
    yield from app.sendfile(resp, "/www/index.html")


@app.route("/data.json")
def send_data(req, resp):
    yield from app.sendfile(resp, "data.json")


@app.route("/jquery-3.4.1.js")
def js(req, resp):
    yield from app.sendfile(resp, "/www/jquery-3.4.1.js")


@app.route("/config")
@require_auth
def get_config(req, resp):
    config = load_config('config.json')
    yield from app.render_template(resp, 'config.html', (config,))


@app.route("/send_config")
@require_auth
def send_config(req, resp):
    if req.method == "GET":
        set_config_handler(req.qs)
        headers = {"Location": "/config"}
        yield from picoweb.start_response(resp, status="303", headers=headers)
    else:  # GET, apparently
        pass


@app.route("/set_limit")
def set_limit(req, resp):
    if req.method == "GET":
        set_limit_handler(req.qs)
        headers = {"Location": "/"}
        yield from picoweb.start_response(resp, status="303", headers=headers)
    else:  # GET, apparently
        pass


loop = asyncio.get_event_loop()
loop.create_task(read_card_loop(pn532))

app.run(debug=1, host=ip_addr, port=80)
