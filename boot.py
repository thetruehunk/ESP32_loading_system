# This file is executed on every boot (including wake-boot from deepsleep)
import esp
import gc
import webrepl
from functions import wifi_init 

esp.osdebug(None)
gc.collect()
wifi_init()
webrepl.start()
#settime()   # убрать и использвать свою функцию
