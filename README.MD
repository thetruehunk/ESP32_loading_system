[![Bintray](https://img.shields.io/bintray/v/blocke/releases/scalajack.svg?maxAge=3600)](https://bintray.com/blocke/releases/scalajack)

*This project is automatisation system*
*for water loading system*

Перед использованием переименовать test_config.json в config.json

<h1>TO DO</h1>

[x] - выбрать и настроить WEB-server
[ ] - Чтение карт типа ""
[ ] - Обработка карт другого формата

[ ] - Работа модулей в режиме клиент-сервер
    [ ] - настройка wifi в зависимости от режима

Создать web-консоль
[x] - Авторизация
[ ] - Главная страница с перечнем карт и установками
[ ] - Страница настроек
[ ] - списание, установка лимитов процедур
[x] - Сортировка карт по номеру
[x] - проверка вводимого значения на валидность
[ ] - day лимит
[x] - обновление страницы https://techtutorialsx.com/2017/09/29/esp32-micropython-getting-the-query-parameters-on-a-picoweb-app/


[ ] - Плановая запись остатков
[ ] - Задержка при выдаче

Обработка параметров запроса Flask
https://stackoverflow.com/questions/10434599/get-the-data-received-in-a-flask-request

Установка picoweb
import upip
upip.install('picoweb')
upip.install('micropython-logging')
После установки возникает проблема с библиотекой uasyncio
необходимо удалить все изкаталога "uasyncio" с модуля
взять core.py и __init__.py из каталога micropython-lib

ampy -p /dev/tty.usbserial-0001 put core.py /lib/uasyncio/core.py
ampy -p /dev/tty.usbserial-0001 put __init__.py /lib/uasyncio/__init__.py

У меня карты mifare classic 1k
С номерами идут EM-Marine
