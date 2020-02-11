# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
import gc
import machine
import webrepl
import wifi
import usocket as socket
from ntptime import settime
import time

wifi.do_connect()
webrepl.start()
gc.collect()
#settime()   # убрать и использвать свою функцию
