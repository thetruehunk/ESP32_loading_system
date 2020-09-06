# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
import gc
import machine
import webrepl
# import usocket as socket
# from ntptime import settime
# import time
from functions import wifi_init 

wifi_init()
webrepl.start()
# gc.collect()
#settime()   # убрать и использвать свою функцию
