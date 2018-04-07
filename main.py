from config import Config
import network
from slider import *
import slider_socket
import uasyncio as asyncio

# setup WiFi
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid=b"SliderMCU", authmode=network.AUTH_WPA_WPA2_PSK, password=b"GoProSlider")

# battery voltage: 2.5 - 4.2 (7.5 - 12.6)
# adc = machine.ADC(machine.Pin(35))
# adc.atten(machine.ADC_ATTN_11DB)

# build slider object
driver = MotorDriver(Config.pin_step, Config.pin_dir, Config.pin_ms1, Config.pin_ms2, Config.pin_ms3)
motor = Motor(driver, Config.pin_edge)
slider = Slider(Dolly(), motor)

# todo: setup pin_edge interrupt as stop motor
Config.pin_edge.irq(trigger=Pin.IRQ_FALLING, handler=motor.stop)

server = slider_socket.SliderServer(driver)
server.start()

# initialize asyncio loop
loop = asyncio.get_event_loop()
loop.call_soon(server.process_all())

loop.run_forever()
server.stop()
