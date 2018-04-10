from config import Config
from machine import I2C
import network
from slider import *
import slider_socket
import ssd1306
import uasyncio as asyncio

# setup WiFi
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid=b"SliderMCU", authmode=network.AUTH_WPA_WPA2_PSK, password=b"GoProSlider")

# setup display
i2c = I2C(scl=Config.display_scl, sda=Config.display_sda)
oled = ssd1306.SSD1306_I2C(Config.display_width, Config.display_height, i2c)
oled.contrast(1)

# build slider object
driver = MotorDriver(Config.pin_step, Config.pin_dir, Config.pin_ms1, Config.pin_ms2, Config.pin_ms3)
motor = Motor(driver, Config.pin_edge)
slider = Slider(motor, oled)

server = slider_socket.SliderServer(slider)
server.start()

# initialize asyncio loop
loop = asyncio.get_event_loop()
loop.call_soon(server.process_all())
loop.run_forever()

server.stop()
