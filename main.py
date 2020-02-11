

import NFC_PN532 as nfc
from machine import Pin, SPI
import machine
import picoweb
import ujson as json
import wifi
import utime as time
import uasyncio as asyncio
import ubinascii


"""Загружаем конфигурационный файл и файл с данными"""
config_file = 'config.json'
with open(config_file) as f:
    config = json.load(f)

data_file = 'data.json'
with open(data_file) as d:
    data_f = json.load(d)

# функция для сохранения данных
def save_data():
    with open(data_file, 'w') as w:
        json.dump(data_f, w)

"""Подключение и настрой реле"""
relay = Pin(18, Pin.OUT)
relay.on()

"""Подключение и настрой считывателя PN532"""
spi_dev = SPI(baudrate=1000000, sck=Pin(5), mosi=Pin(23), miso=Pin(19)) 
cs = Pin(22, Pin.OUT)
cs.on()

# Инициализация сенсора 
pn532 = nfc.PN532(spi_dev,cs)
ic, ver, rev, support = pn532.get_firmware_version()
print('Found PN532 with firmware version: {0}.{1}'.format(ver, rev))

# Конфигурация PN532 для работы с MiFare картами
pn532.SAM_configuration()

def read_nfc(dev, tmot):
    """Accepts a device and a timeout in millisecs """
    print('Reading...')
    uid = dev.read_passive_target(timeout=tmot)
    if uid is None:
        print('CARD NOT FOUND')
    else:
        numbers = [i for i in uid]
        string_ID = '{}-{}-{}-{}'.format(*numbers)
        print(string_ID)
        print('Found card with UID:', [hex(i) for i in uid])
        print('Number_id: {}'.format(string_ID))
        # проверяем наличие карты в списке и баланс карты
        if string_ID in  data_f and data_f[string_ID] > 0:
            # if выдано 2 порции day limit
            relay.off()
            # задержка реле (время налива)
            time.sleep(2.5)
            #await asyncio.sleep(1)
            relay.on()
            print('Loading')
            # списываем выдачу одну процедуру с баланса
            print(data_f[string_ID])
            print('process....')
            data_f[string_ID] -=1
            print(data_f[string_ID])
            # сейчас сохраняем данные после каждого списания
            save_data()
            time.sleep(3)
        else:
            pass


def read_card_loop():
    while True:
        read_nfc(pn532, 500)
        await asyncio.sleep(1)


def set_proc_limit(qs):
    pre_parse = qs.replace('_','=')
    parse = pre_parse.split('=')
    print(parse)
    number = parse[0]
    card = parse[1]
    value = parse[2]
    data_f[number][card] = int(value)
    print(data_f[number][card])
    save_data()



app = picoweb.WebApp(__name__)

def require_auth(func):
    def auth(req, resp):
        auth = req.headers.get(b"Authorization")
        if not auth:
            yield from resp.awrite(
                'HTTP/1.0 401 NA\r\n'
                'WWW-Authenticate: Basic realm="Picoweb Realm"\r\n'
                '\r\n'
            )
            return

        auth = auth.split(None, 1)[1]
        auth = ubinascii.a2b_base64(auth).decode()
        req.username, req.passwd = auth.split(":", 1)

        if not ((req.username == config["web-login"]) and  (req.passwd == config["web-passwd"])):
            yield from resp.awrite(
                'HTTP/1.0 401 NA\r\n'
                'WWW-Authenticate: Basic realm="Picoweb Realm"\r\n'
                '\r\n'
            )
            return

        yield from func(req, resp)

    return auth


@app.route("/")
@require_auth
def send_index(req, resp):
    yield from app.sendfile(resp, 'index.html')

@app.route("/data.json")
def send_data(req, resp):
    yield from app.sendfile(resp, 'data.json')

@app.route("/set_total_limit")
def set_total_limit(req, resp):
    if req.method == "GET":
        set_proc_limit(req.qs)
        headers = {"Location": "/"}
        yield from picoweb.start_response(resp, status="303", headers=headers)

    else:  # GET, apparently
        pass


loop = asyncio.get_event_loop()
loop.create_task(read_card_loop())

app.run(debug=1, host=wifi.ip_address, port=80)
